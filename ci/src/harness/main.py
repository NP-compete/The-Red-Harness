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
from dagger import DefaultPath, Doc, dag, function, object_type

PYTHON = "python:3.12-slim-bookworm"
#: `engines` in services/ui/package.json asks for >=22.13.
NODE = "node:22-slim"

#: Kept out of the build context. `.venv` and `node_modules` are
#: gigabytes that the container rebuilds anyway, and shipping `.git`
#: into a cache key makes every commit a cache miss.
IGNORE = [
    ".venv",
    "node_modules",
    ".git",
    ".local",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
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
        `.github` that is not in the image.
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
        jobs.append(self._named("test", self.test(source)))
        jobs.append(self._named("ui", self.ui(source)))

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
