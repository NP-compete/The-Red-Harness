"""The pull-request checks, as functions that run in containers.

This replaces CI-1 — "every pipeline step is a Makefile target" —
and the two tests that held it up. CI-1 existed to stop `make ci`
and the pipeline drifting apart, and it worked, but only on *which
checks run*: the Makefile's own note admitted the rest of the gap,
that each side "runs against whatever toolchain you have. A version
difference will still surprise somebody."

A Dagger function closes that. One list and one toolchain: the
container defined in `base()` is what runs on a laptop and what
runs on a runner, so "works locally" and "passes CI" stop being two
questions.

    dagger -m ci call ci              everything
    dagger -m ci call tautologies     one check
    dagger -m ci call test --source=.

Every function takes the source directory explicitly. Nothing here
reads the host filesystem, which is what makes the result the same
wherever it runs.
"""

from collections.abc import Awaitable
from typing import Annotated

import dagger
from dagger import DefaultPath, Doc, Ignore, dag, function, object_type

#: Docker Hub, through Google's pull-through mirror. Not a
#: preference: two runs in a row died on
#: `failed to copy: read: connection reset by peer` pulling
#: `node:22-slim` and `pgvector/pgvector:pg16` straight from
#: docker.io, which took five checks and the whole integration tier
#: with them and had nothing to do with the code. `mirror.gcr.io`
#: serves the same digests and does not rate-limit a runner.
#: `mcr.microsoft.com` and `ghcr.io` images below are left alone —
#: they are not the ones that failed.
HUB = "mirror.gcr.io"

PYTHON = f"{HUB}/library/python:3.12-slim-bookworm"
#: `engines` in services/ui/package.json asks for >=22.13.
NODE = f"{HUB}/library/node:22-slim"
#: Tracks `@playwright/test` in services/ui/package.json exactly: the
#: image ships the browser build that version expects, and a mismatch
#: fails every test in 3ms with "Executable doesn't exist".
PLAYWRIGHT = (
    "mcr.microsoft.com/playwright:v1.64.0-noble@sha256:"
    "06a9939e57531807f8d5fd76ce44b53165ffb7d7501d87ab10e285c20b1e971f"
)
TRIVY = "ghcr.io/aquasecurity/trivy:0.76.2"
GITLEAKS = "ghcr.io/gitleaks/gitleaks:v8.28.0"
#: The datastores `compose_tier` binds. The same images the compose
#: file names, so the tier is testing what a developer runs.
POSTGRES = f"{HUB}/pgvector/pgvector:pg16"
REDIS = f"{HUB}/library/redis:7-alpine"

#: Kept out of the build context, and now actually applied — this
#: list sat here unused while every call uploaded the whole working
#: tree, `.venv` and `node_modules` included. That is 3.5 GB of the
#: 4.8, rebuilt in the container anyway, and it is why a single
#: check took minutes before it had run anything.
#:
#: `.git` is not here, unlike the first draft of this list.
#: `gitleaks` reads every commit the branch can see, and
#: `pre-commit` wants a repository to enumerate files from; without
#: the history both pass by having nothing to look at.
IGNORE = [
    # `.env` first, and for a different reason from the rest. It is
    # gitignored, so a runner's checkout has none — but a laptop's
    # working tree does, and Dagger uploads the host directory, not
    # the commit. So every local run was handing its containers a
    # developer's real `.env`: a Fernet key, a service-account
    # private key, `ENABLE_AUTH=false`. That is both a secret in a
    # container that did not need one and the reason "it passes
    # locally" kept meaning nothing — the agent and the interface
    # were reading configuration the pipeline would never have.
    ".env",
    "**/.env",
    "**/.venv",
    "**/node_modules",
    "**/dist",
    "**/__pycache__",
    "**/.pytest_cache",
    "**/.ruff_cache",
    "**/.mypy_cache",
    "**/coverage",
    "**/htmlcov",
    ".local",
    "ci/sdk",
]

#: The checks that need nothing but the source and the dependencies.
#: Each is (function name, argv). Adding one here adds it to `ci`.
CHECKS: dict[str, list[str]] = {
    # Taken from the Makefile recipes, not from the target names —
    # `tautologies` runs `tautological_asserts.py`, and guessing cost
    # a full container build to find out.
    "validate_config": ["python", "-m", "agent.src.agent.config.validate"],
    "feature_registry": ["python", "scripts/ci/feature_registry.py"],
    "capability_gates": ["python", "scripts/ci/capability_gates.py"],
    "safe_defaults": ["python", "scripts/ci/safe_defaults.py"],
    "failure_logs": ["python", "scripts/ci/failure_logs_name_things.py"],
    "tautologies": ["python", "scripts/ci/tautological_asserts.py"],
    "blocking_calls": ["python", "scripts/ci/blocking_calls.py"],
    "background_tasks": ["python", "scripts/ci/background_tasks.py"],
    "datastore_check": ["python", "scripts/ci/datastore_images.py"],
    "render_deployment": ["python", "scripts/deploy/render_deployment.py", "--check"],
    "evals_offline": ["python", "-m", "scripts.evals.run_offline_evals"],
}

Source = Annotated[
    dagger.Directory,
    Doc("The repository. Defaults to the directory this module lives in."),
    DefaultPath("/"),
    Ignore(IGNORE),
]


@object_type
class Harness:
    """The CI checks, each runnable on its own or all together."""

    @function
    def base(self, source: Source) -> dagger.Container:
        """The container every check runs in.

        Dependencies install from `pyproject.toml` alone, before the
        source is mounted, so editing code does not reinstall them.
        That ordering is the whole reason this is fast on the second
        run.
        """
        return (
            dag.container()
            .from_(PYTHON)
            .with_exec(["apt-get", "update"])
            # git and make because tests shell out to them; nodejs
            # because `harness ui` refuses without it and a test
            # checks that refusal; kubectl because the deployment
            # tests render the overlays with `kubectl kustomize` and
            # would otherwise skip — a check that skips in CI is a
            # check that is not running.
            .with_exec(
                [
                    "apt-get",
                    "install",
                    "-y",
                    "--no-install-recommends",
                    "git",
                    "make",
                    "nodejs",
                    "curl",
                    "ca-certificates",
                ]
            )
            .with_exec(
                [
                    "sh",
                    "-c",
                    "curl -fsSL https://dl.k8s.io/release/"
                    "$(curl -fsSL https://dl.k8s.io/release/stable.txt)"
                    "/bin/linux/$(dpkg --print-architecture)/kubectl "
                    "-o /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl",
                ]
            )
            .with_exec(["pip", "install", "--no-cache-dir", "uv"])
            .with_mounted_cache("/root/.cache/uv", dag.cache_volume("uv"))
            .with_workdir("/src")
            # `-r pyproject.toml` installs the dependencies *without*
            # building the project, which is what we want: hatchling
            # validates the readme, resolves `packages`, and chases
            # every `force-include` before it will produce an editable
            # wheel, so a dependency-only layer kept failing on files
            # that have nothing to do with dependencies. The project
            # itself needs no install — PYTHONPATH below reaches it.
            .with_file("/src/pyproject.toml", source.file("pyproject.toml"))
            .with_exec(
                [
                    "uv",
                    "pip",
                    "install",
                    "--system",
                    "-r",
                    "pyproject.toml",
                    "--extra",
                    "dev",
                ]
            )
            .with_directory("/src", source.without_directory("ci/sdk"))
            # Not root. The runtime image runs as 65532, and a check
            # running as root is a check that cannot see a permission
            # problem: `test_falls_back_when_the_path_cannot_be_made`
            # asserts `/app/data` is unwritable, which is true on a
            # laptop and false for root, so it failed here and only
            # here.
            .with_exec(["useradd", "--create-home", "--uid", "65532", "ci"])
            .with_exec(["chown", "-R", "ci:ci", "/src"])
            .with_env_variable("PYTHONPATH", "/src/services:/src")
            # `tldextract` fetches the public-suffix list on first
            # use. In a fresh container that is a cache miss nine PII
            # tests fail on; priming it here costs one request per
            # image build instead of one per run.
            .with_user("ci")
            .with_env_variable("HOME", "/home/ci")
            .with_exec(
                [
                    "python",
                    "-c",
                    "import tldextract; tldextract.TLDExtract()('a.co.uk')",
                ]
            )
        )

    @function
    async def check(
        self,
        source: Source,
        name: Annotated[str, Doc("Which check, as named in CHECKS")],
    ) -> str:
        """Run one named check and return what it printed."""
        if name not in CHECKS:
            raise ValueError(f"no check called {name!r}; have {sorted(CHECKS)}")
        out: str = await self.base(source).with_exec(CHECKS[name]).stdout()
        return out

    @function
    async def test(self, source: Source) -> str:
        """The whole suite, except what needs a model or a cluster."""
        out: str = await (
            self.base(source)
            .with_exec(
                [
                    "python",
                    "-m",
                    "pytest",
                    "tests",
                    "-m",
                    "not skills and not nightly",
                    "-q",
                    # The long pole: 6m38s of a 9m13s run. One worker
                    # per core takes it to about a minute.
                    "-n",
                    "auto",
                    "--dist=loadfile",
                ]
            )
            .stdout()
        )
        return out

    @function
    async def pytest(
        self,
        source: Source,
        args: Annotated[str, Doc("Arguments to pass to pytest, space separated")],
    ) -> str:
        """An arbitrary pytest run in the suite's own container.

        For the failure that only happens there. Without this the
        only way to reproduce one was to run the whole suite and
        read thirteen minutes of log.
        """
        # `shlex.split`, not `str.split`. The first version broke
        # `-m 'integration and not nightly'` into five tokens and
        # pytest exited 4 — a usage error that looked like a 35-second
        # test run, which is the worst thing a measuring instrument
        # can do.
        import shlex

        out: str = await (
            self.base(source)
            .with_exec(["python", "-m", "pytest", *shlex.split(args)])
            .stdout()
        )
        return out

    @function
    async def lint(self, source: Source) -> str:
        """Ruff over the whole tree. Not part of `ci`, and why.

        The repository has never passed this: 590 findings with
        `tests/` included, 16 without, and 50 files that `ruff
        format` would rewrite. Pre-commit runs ruff with `--fix`
        over *changed* files and excludes `^tests/`, so the tree at
        large was never held to it. Wiring this into `ci` would not
        be porting a check — it would be adding one, and failing
        every pull request until somebody fixed 66 things nobody
        asked them to. Call it directly when that is the work.
        """
        out: str = await (
            self.base(source)
            .with_exec(["ruff", "check", "."])
            .with_exec(["ruff", "format", "--check", "."])
            .stdout()
        )
        return out

    @function
    def ui_base(self, source: Source) -> dagger.Container:
        """The interface's container.

        `npm ci` runs in place at `/src/services/ui` with only the
        lockfile present, so a component edit does not reinstall
        node_modules. `.github` comes along because two of the
        interface's tests read the workflows — they check the UI's
        own CI job still exists — and without it they look for a
        `.github` that is not in the image. `tests/fixtures` carries
        the OpenAPI baseline that `contract:check` regenerates from.
        """
        ui = source.directory("services/ui")
        return (
            dag.container()
            .from_(NODE)
            .with_mounted_cache("/root/.npm", dag.cache_volume("npm"))
            .with_workdir("/src/services/ui")
            .with_file("/src/services/ui/package.json", ui.file("package.json"))
            .with_file(
                "/src/services/ui/package-lock.json", ui.file("package-lock.json")
            )
            .with_exec(["npm", "ci"])
            .with_directory("/src/services/ui", ui.without_directory("node_modules"))
            .with_directory("/src/.github", source.directory(".github"))
            .with_file(
                "/src/tests/fixtures/openapi-baseline.json",
                source.file("tests/fixtures/openapi-baseline.json"),
            )
            # `every-check-is-run.test.ts` reads this module to check
            # that the interface's checks are still gathered by `ci`.
            # It used to read `.github/workflows/ui.yml`, which no
            # longer exists; without the pipeline here it fails with
            # ENOENT, which is the guard working and saying the wrong
            # thing.
            .with_directory("/src/ci/src", source.directory("ci/src"))
        )

    @function
    async def ui_lint(self, source: Source) -> str:
        """Eslint over the interface."""
        out: str = await self.ui_base(source).with_exec(["npm", "run", "lint"]).stdout()
        return out

    @function
    async def ui_checks(self, source: Source) -> str:
        """Three guards over files that are generated and committed.

        `i18n-missing` says so in its own docstring — "usable in CI" —
        and for a long time ran nowhere: a key a component asks for
        and the catalogue lacks renders as `settings.saveLabel` on
        screen, because i18next falls back to the key and nothing
        else notices. The contract check compares the interface's
        generated types against the agent's OpenAPI baseline.
        """
        out: str = await (
            self.ui_base(source)
            .with_exec(["npm", "run", "i18n:missing"])
            .with_exec(["npm", "run", "i18n:report"])
            .with_exec(["npm", "run", "contract:check"])
            .stdout()
        )
        return out

    @function
    def ui_dist(self, source: Source) -> dagger.Directory:
        """The built SPA and BFF, as a directory `e2e` can mount.

        This is why the build and the end-to-end run are one pipeline
        rather than two jobs and an artifact between them. The
        artifact was the bug: vite writes its asset manifest to a
        dotted directory, upload-artifact drops dotted paths by
        default, and the server that reads that manifest at boot
        refused to start — reported as "timed out waiting 30000ms".
        A Dagger directory has no such rule.
        """
        return (
            self.ui_base(source)
            .with_exec(["npm", "run", "build"])
            .directory("/src/services/ui/dist")
        )

    @function
    async def ui_build(self, source: Source) -> str:
        """The interface builds. Shares its layer with `ui_dist`."""
        out: str = await (
            self.ui_base(source).with_exec(["npm", "run", "build"]).stdout()
        )
        return out

    def _e2e_container(self, source: Source) -> dagger.Container:
        """Playwright's own image, with the built BFF in it.

        `config/` comes along because the server watches
        `config/agent/PROMPT.md` at boot.
        """
        ui = source.directory("services/ui")
        return (
            dag.container()
            .from_(PLAYWRIGHT)
            .with_mounted_cache("/root/.npm", dag.cache_volume("npm"))
            .with_workdir("/src/services/ui")
            .with_file("/src/services/ui/package.json", ui.file("package.json"))
            .with_file(
                "/src/services/ui/package-lock.json", ui.file("package-lock.json")
            )
            .with_exec(["npm", "ci"])
            .with_directory("/src/services/ui", ui.without_directory("node_modules"))
            .with_directory("/src/services/ui/dist", self.ui_dist(source))
            .with_directory("/src/config", source.directory("config"))
            .with_env_variable("CI", "true")
        )

    @function
    async def e2e(self, source: Source) -> str:
        """Playwright against the built BFF, in Playwright's own image."""
        # Allowed to fail, so the report survives it. The old
        # workflow uploaded `playwright-report/` with `if: always()`;
        # a `with_exec` that raises takes its container with it, and
        # a failing browser test you cannot look at is a failing test
        # you cannot fix. Read the code, keep the report, then fail.
        done = self._e2e_container(source).with_exec(
            ["npx", "playwright", "test"], expect=dagger.ReturnType.ANY
        )
        code = await done.exit_code()
        out: str = await done.stdout()
        if code != 0:
            raise RuntimeError(
                f"{out}\n\nplaywright exited {code}. "
                "`dagger -m ci call e-2-e-report export --path=playwright-report` "
                "for the traces."
            )
        return out

    @function
    def e2e_report(self, source: Source) -> dagger.Directory:
        """The Playwright report, whether or not the run passed."""
        return (
            self._e2e_container(source)
            .with_exec(["npx", "playwright", "test"], expect=dagger.ReturnType.ANY)
            .directory("/src/services/ui/playwright-report")
        )

    @function
    async def ui(self, source: Source) -> str:
        """The interface's unit suite.

        It ran in a workflow of its own and in no local command, so
        "the tests pass" meant the Python ones. Here it is one job
        among the rest.
        """
        out: str = (
            await self.ui_base(source)
            .with_exec(["npm", "run", "test:coverage"])
            .stdout()
        )
        return out

    @function
    async def pre_commit(self, source: Source) -> str:
        """Every pre-commit hook over the whole tree.

        The mypy hook is `entry: .venv/bin/mypy` with `language:
        system`, which is right on a laptop and wrong here — nothing
        installs a virtualenv in this container, it installs
        system-wide. A symlink at the path the config names is
        cheaper than two ways of saying where mypy is.
        """
        out: str = await (
            self.base(source)
            .with_user("root")
            .with_exec(["mkdir", "-p", "/src/.venv/bin"])
            .with_exec(["sh", "-c", "ln -sf $(command -v mypy) /src/.venv/bin/mypy"])
            .with_exec(["chown", "-R", "ci:ci", "/src/.venv"])
            .with_user("ci")
            .with_exec(["git", "config", "--global", "--add", "safe.directory", "/src"])
            .with_exec(["pre-commit", "run", "--all-files", "--show-diff-on-failure"])
            .stdout()
        )
        return out

    @function
    async def gitleaks(self, source: Source) -> str:
        """Every commit this branch can see, not just the staged ones.

        The pre-commit hook scans `--staged`, which in a pipeline is
        empty — it passes by having nothing to look at. This reads
        the history, which is the only place a secret that was
        committed and then deleted still is.
        """
        out: str = await (
            dag.container()
            .from_(GITLEAKS)
            .with_entrypoint([])
            .with_directory("/src", source)
            .with_workdir("/src")
            .with_exec(["git", "config", "--global", "--add", "safe.directory", "/src"])
            .with_exec(
                [
                    "gitleaks",
                    "git",
                    "--config",
                    ".gitleaks.toml",
                    "--log-opts=--all",
                    "--redact",
                    "--verbose",
                ]
            )
            .stdout()
        )
        return out

    def _trivy(self) -> dagger.Container:
        """Trivy, with its vulnerability database cached between runs."""
        return (
            dag.container()
            .from_(TRIVY)
            .with_entrypoint([])
            .with_mounted_cache("/root/.cache/trivy", dag.cache_volume("trivy"))
        )

    @function
    async def license_scan(self, source: Source) -> str:
        """The licences of everything this repository pulls in."""
        out: str = await (
            self._trivy()
            .with_directory("/src", source)
            .with_workdir("/src")
            .with_exec(
                [
                    "trivy",
                    "filesystem",
                    "--scanners",
                    "license",
                    # A forbidden licence is HIGH or CRITICAL and
                    # still fails. UNKNOWN is reported and does not:
                    # every one of the twelve is trivy declining to
                    # parse `SEE LICENSE IN LICENSE` on a package
                    # whose licence file says MIT. That is trivy not
                    # knowing, which is worth reading and is not a
                    # licence violation — and `required-checks.yml`
                    # already calls this check "a conversation rather
                    # than a build failure".
                    "--severity",
                    "HIGH,CRITICAL",
                    "--exit-code",
                    "1",
                    "--config",
                    "trivy-license.yaml",
                    ".",
                ]
            )
            # The unclassified ones, named rather than dropped. A
            # check that stops failing and stops reporting has not
            # been made advisory, it has been deleted.
            .with_exec(
                [
                    "trivy",
                    "filesystem",
                    "--scanners",
                    "license",
                    "--severity",
                    "UNKNOWN",
                    "--exit-code",
                    "0",
                    "--config",
                    "trivy-license.yaml",
                    ".",
                ]
            )
            .stdout()
        )
        return out

    @function
    def image(self, source: Source) -> dagger.Container:
        """The runtime image, built from the Containerfile."""
        return source.docker_build(dockerfile="Containerfile")

    @function
    async def image_scan(self, source: Source) -> str:
        """Trivy over the image this repository ships.

        The image is handed over as a tarball rather than a tag:
        there is no daemon here holding a `scan-target:` to refer to,
        which is the point — nothing in this depends on what the
        runner happens to have loaded.
        """
        out: str = await (
            self._trivy()
            .with_file("/image.tar", self.image(source).as_tarball())
            .with_file("/.trivyignore", source.file(".trivyignore"))
            .with_workdir("/")
            .with_exec(
                [
                    "trivy",
                    "image",
                    "--quiet",
                    "--input",
                    "/image.tar",
                    "--scanners",
                    "vuln",
                    "--severity",
                    "CRITICAL,HIGH",
                    "--ignorefile",
                    "/.trivyignore",
                    "--exit-code",
                    "1",
                ]
            )
            .stdout()
        )
        return out

    def _image_report(self, source: Source, fmt: str, out: str) -> dagger.File:
        """One trivy report over the image, in `fmt`, as a file."""
        return (
            self._trivy()
            .with_file("/image.tar", self.image(source).as_tarball())
            .with_workdir("/")
            .with_exec(
                [
                    "trivy",
                    "image",
                    "--input",
                    "/image.tar",
                    "--scanners",
                    "vuln",
                    "--format",
                    fmt,
                    "--output",
                    out,
                    "--exit-code",
                    "0",
                ]
            )
            .file(out)
        )

    @function
    def image_sbom(self, source: Source) -> dagger.File:
        """A CycloneDX bill of materials for the image."""
        return self._image_report(source, "cyclonedx", "/sbom.cdx.json")

    @function
    def image_sarif(self, source: Source) -> dagger.File:
        """The image's vulnerabilities as SARIF, for the Security tab."""
        return self._image_report(source, "sarif", "/trivy-results.sarif")

    def datastores(self, container: dagger.Container) -> dagger.Container:
        """Bind Postgres and Redis to a container, and point it at them."""
        postgres = (
            dag.container()
            .from_(POSTGRES)
            .with_env_variable("POSTGRES_PASSWORD", "postgres")
            .with_env_variable("POSTGRES_DB", "template_agent")
            .with_exposed_port(5432)
            .as_service(use_entrypoint=True)
        )
        redis = (
            dag.container()
            .from_(REDIS)
            .with_exposed_port(6379)
            .as_service(use_entrypoint=True)
        )
        return (
            container.with_service_binding("postgres", postgres)
            .with_service_binding("redis", redis)
            .with_env_variable("POSTGRES_HOST", "postgres")
            .with_env_variable("POSTGRES_PORT", "5432")
            .with_env_variable("POSTGRES_DB", "template_agent")
            .with_env_variable("POSTGRES_USER", "postgres")
            .with_env_variable("POSTGRES_PASSWORD", "postgres")
            .with_env_variable("REDIS_URL", "redis://redis:6379/0")
        )

    @function
    async def agent_boot(self, source: Source) -> str:
        """Start the agent against bound datastores and return its log.

        A service that will not come up is invisible from the outside:
        Dagger waits on the port and prints "3 steps running" until
        somebody gives up. This runs the same command in the
        foreground so the reason is readable.
        """
        probe = (
            "aegra dev --host 0.0.0.0 --port 5002 --no-db-check --no-reload "
            "> /tmp/a.log 2>&1 & "
            "for i in $(seq 1 60); do "
            "curl -sf -o /dev/null http://127.0.0.1:5002/health && "
            "{ echo UP_AFTER_${i}s; break; }; sleep 1; done; "
            "echo ---; tail -40 /tmp/a.log"
        )
        out: str = await (
            self.datastores(self.base(source)).with_exec(["sh", "-c", probe]).stdout()
        )
        return out

    @function
    async def compose_tier(self, source: Source) -> str:
        """The tests that need real datastores and a running agent.

        They were the last thing outside this module: a job that
        declared Postgres and Redis as service containers, started
        the agent in a background shell and polled a health endpoint
        with `for _ in $(seq 1 60)`. Dagger's service bindings do all
        three, and — unlike the runner's — they work on a laptop.
        """
        agent = (
            self.datastores(self.base(source))
            # The agent refuses to start without this when any MCP
            # server stores tokens, which eight of them do. A fixed
            # value: these tests seal nothing anybody reads, and a
            # generated one would make the container's cache key
            # change on every run.
            .with_env_variable(
                "MCP_TOKEN_ENCRYPTION_KEY",
                "Zm9yLXRoZS1pbnRlZ3JhdGlvbi10aWVyLW9ubHktMzJiPQ==",
            )
            .with_exposed_port(5002)
            # `--host 0.0.0.0`, which is not the default. `aegra dev`
            # binds 127.0.0.1, a service binding reaches the container
            # from outside, and Dagger waits for the port forever — the
            # first run of this sat at "3 steps running" for an hour
            # and forty minutes with nothing to say.
            #
            # `--no-reload` because a file watcher in a container
            # nobody is editing is a second process to signal.
            .with_exec(
                [
                    "aegra",
                    "dev",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "5002",
                    "--no-db-check",
                    "--no-reload",
                ]
            )
            .as_service()
        )
        # The datastores are bound to the *agent*, not to this
        # container. These tests talk to a running agent over HTTP and
        # never to Postgres directly — and handing them a reachable
        # one is actively harmful: `agent.aegra.shutdown` registers an
        # atexit handler that closes the pool, and at interpreter
        # shutdown that raises `RuntimeError: Event loop is closed`
        # and pytest exits 3 having run every test successfully.
        out: str = await (
            self.base(source)
            .with_service_binding("agent", agent)
            .with_env_variable("LANGGRAPH_API_URL", "http://agent:5002")
            .with_env_variable("AGENT_BASE_URL", "http://agent:5002")
            # Unbuffered and one line per test, because this tier was
            # cancelled twice at the job's timeout having printed
            # nothing at all. The same selection takes 101s in this
            # container on a laptop and 95s on the host, so whatever
            # costs the other fifty minutes on a runner is not the
            # tests — and silence is the reason that took three
            # rounds to establish rather than one.
            .with_env_variable("PYTHONUNBUFFERED", "1")
            .with_exec(
                [
                    "python",
                    "-m",
                    "pytest",
                    "tests",
                    "-m",
                    "integration and not nightly",
                    "-v",
                    "--color=no",
                    # A deadline, because a hung test here is
                    # indistinguishable from a slow one from the
                    # outside: this sat at "3 steps running" for an
                    # hour and forty minutes the first time.
                    "--timeout=180",
                    "--timeout-method=thread",
                    # Which of the ninety-one are the slow ones. They
                    # have never run in CI before, so nobody knows.
                    "--durations=20",
                ]
            )
            .stdout()
        )
        return out

    @function
    async def ci(self, source: Source) -> str:
        """Every check, concurrently. Non-zero if any of them fail.

        Concurrency is the reason for the rewrite: these ran in
        sequence as sixteen Makefile targets, each paying for its own
        interpreter start.
        """
        import asyncio

        async def one(name: str) -> tuple[str, str | None]:
            """Run one named check and return its name and failure, if any."""
            try:
                await self.check(source, name)
            except Exception as failed:  # noqa: BLE001
                return name, str(failed)
            return name, None

        jobs = [one(name) for name in CHECKS]
        for name, work in (
            ("test", self.test(source)),
            ("ui", self.ui(source)),
            ("ui_lint", self.ui_lint(source)),
            ("ui_checks", self.ui_checks(source)),
            ("ui_build", self.ui_build(source)),
            ("e2e", self.e2e(source)),
            ("pre_commit", self.pre_commit(source)),
            ("gitleaks", self.gitleaks(source)),
            # `image_scan` is out for the same reason as
            # `compose_tier`, only sharper: it builds the whole
            # runtime image and exports it as a tarball, which is the
            # image twice on disk. On a runner with 14 GB that filled
            # the engine's snapshot store and took nine *other*
            # checks down with it — `no space left on device`
            # reported as a failing config validator. It has its own
            # job in `build-base-image.yml`, which is where the image
            # is built anyway.
            # `license_scan` is deliberately absent: `required-checks.yml`
            # calls it advisory — "a conversation rather than a build
            # failure" — and a function in this list is a blocking one.
            # Its workflow calls it directly. `compose_tier` is out
            # for a different reason: it brings up three services and
            # is minutes slower than everything else here put
            # together, and a job that hangs inside `ci` takes the
            # other twenty with it. Its own job, its own timeout.
        ):
            jobs.append(self._named(name, work))

        results = await asyncio.gather(*jobs)
        failed = [(name, why) for name, why in results if why]

        lines = [f"{'FAIL' if why else 'ok  '}  {name}" for name, why in results]
        if failed:
            lines.append("")
            for name, why in failed:
                lines.append(f"── {name}\n{why}")
            raise RuntimeError("\n".join(lines))
        return "\n".join(lines)

    @staticmethod
    async def _named(name: str, work: Awaitable[object]) -> tuple[str, str | None]:
        """Await `work` and return `name` with its failure, if any."""
        try:
            await work
        except Exception as failed:  # noqa: BLE001
            return name, str(failed)
        return name, None
