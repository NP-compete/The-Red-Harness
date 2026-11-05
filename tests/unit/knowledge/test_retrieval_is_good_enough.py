"""What the corpus actually scores, pinned so it cannot fall."""

from __future__ import annotations

from agent.src.knowledge.retrieval_quality import Case, measure
from agent.src.knowledge.scopes import Scope, Viewer
from agent.src.knowledge.store import Document, InMemoryStore

RECALL_AT = 5
PRECISION_AT = 1

FLOOR_RECALL = 1.0
FLOOR_PRECISION = 0.92

CORPUS: list[tuple[str, str]] = [
    (
        "rotate-signing-key",
        "Rotating the signing key. The token signing key is replaced on a "
        "ninety day cycle. Generate the replacement, publish it alongside the "
        "current key, wait one token lifetime, then withdraw the old one. "
        "Never withdraw before the wait or every issued token is refused.",
    ),
    (
        "rotate-logs",
        "Rotating logs. Application logs are rotated nightly and kept for "
        "thirty days. Rotation is handled by the platform; no action is "
        "needed unless a volume fills, in which case reduce the retention "
        "window rather than deleting files by hand.",
    ),
    (
        "signing-key-storage",
        "Where the signing key lives. The key is held in the secret store and "
        "read at startup. It is never written to disk and never logged. A "
        "deployment that cannot read it refuses to start rather than issuing "
        "tokens nobody can verify.",
    ),
    (
        "err-4021",
        "ERR-4021 means the upstream connection was refused. Check the "
        "allowlist first: the most common cause is a host added to the "
        "configuration but not to the egress policy.",
    ),
    (
        "err-4022",
        "ERR-4022 means the upstream connection timed out. This is a "
        "different fault from a refusal and usually means the host is "
        "reachable but overloaded.",
    ),
    (
        "egress-policy",
        "The egress policy lists every host this deployment may reach. A host "
        "missing from it is refused at connection time, which surfaces to the "
        "caller as a connection error rather than a policy message.",
    ),
    (
        "account-id-format",
        "The account_id field is a twenty six character string beginning with "
        "the region code. It is not a number and must not be parsed as one; "
        "leading zeroes are significant.",
    ),
    (
        "account-deletion",
        "Deleting an account removes its documents, its memories and its "
        "artifacts. The account_id is retained in the audit record because an "
        "audit trail that forgets who acted is not an audit trail.",
    ),
    (
        "rate-limits",
        "Each person has a daily allowance of requests. When it is spent the "
        "agent refuses with the time the allowance resets, rather than "
        "failing silently or queueing indefinitely.",
    ),
    (
        "rate-limit-shared",
        "A shared deployment divides its allowance between its people rather "
        "than giving each the full amount. One person cannot spend the whole "
        "deployment's budget in an afternoon.",
    ),
    (
        "approval-policy",
        "A write is put to a person for approval when the run has already "
        "read something from outside the conversation. The question names "
        "where that text came from, because text from outside is true of "
        "almost every useful run and tells nobody anything.",
    ),
    (
        "approval-identity",
        "Approval is identity bound. One person cannot answer another's "
        "pending question, because the answer carries whatever authority that "
        "person has.",
    ),
    (
        "backups",
        "Backups run nightly and are kept for thirty five days. A restore is "
        "tested quarterly; a backup nobody has restored is a hope rather than "
        "a backup.",
    ),
    (
        "restore-procedure",
        "To restore, stop writes, pick the most recent backup before the "
        "fault, restore to a new volume, and verify before switching traffic. "
        "Never restore over the live volume.",
    ),
    (
        "onboarding",
        "A new person gets access through their team in the directory. "
        "Membership is never recorded locally, because a local copy is a "
        "second place deciding who is in what.",
    ),
    (
        "offboarding",
        "When somebody leaves, removing them from the directory removes their "
        "access everywhere. There is no second list to remember.",
    ),
    (
        "tls-versions",
        "Only TLS 1.2 and 1.3 are accepted. Older versions are refused at the "
        "edge rather than being downgraded.",
    ),
    (
        "certificate-renewal",
        "Edge certificates renew automatically thirty days before expiry. A "
        "renewal that fails raises an alert; it does not retry silently until "
        "the certificate expires.",
    ),
    (
        "data-retention",
        "Conversations are kept for ninety days unless a person deletes them "
        "sooner. Deleting a conversation deletes its attachments with it.",
    ),
    (
        "export-your-data",
        "One action exports everything held about a person: their documents, "
        "their memories, their artifacts and their conversations.",
    ),
]

CASES = [
    Case(
        query="how do I rotate the token signing key", relevant={"rotate-signing-key"}
    ),
    Case(query="where is the signing key stored", relevant={"signing-key-storage"}),
    Case(query="what does ERR-4021 mean", relevant={"err-4021"}),
    Case(
        query="upstream connection refused by the egress policy",
        relevant={"err-4021", "egress-policy"},
    ),
    Case(query="is account_id a number", relevant={"account-id-format"}),
    Case(
        query="what happens to my documents when an account is deleted",
        relevant={"account-deletion"},
    ),
    Case(
        query="why was my request refused for spending my allowance",
        relevant={"rate-limits"},
    ),
    Case(
        query="can one person use the whole deployment allowance",
        relevant={"rate-limit-shared"},
    ),
    Case(
        query="can somebody else answer my pending approval",
        relevant={"approval-identity"},
    ),
    Case(
        query="how do I restore from a backup after a fault",
        relevant={"restore-procedure", "backups"},
    ),
    Case(
        query="removing access when somebody leaves the company",
        relevant={"offboarding"},
    ),
    Case(
        query="which TLS versions are accepted at the edge",
        relevant={"tls-versions"},
    ),
    Case(
        query="how long are conversations kept",
        relevant={"data-retention"},
    ),
    Case(
        query="export everything held about me",
        relevant={"export-your-data"},
    ),
]


def _store() -> InMemoryStore:
    store = InMemoryStore()
    for document_id, text in CORPUS:
        store.add(
            Document(id=document_id, text=text, scope=Scope.AGENT, title=document_id)
        )
    return store


def _searcher():
    store = _store()
    viewer = Viewer(subject="ada", teams=(), thread_id=None)

    def search(query: str) -> list[str]:
        hits = store.search_scored(
            query, scope=Scope.AGENT, viewer=viewer, top_k=RECALL_AT
        )
        return [hit.document.id for hit in hits]

    return search


def _recall() -> float:
    return measure(_searcher(), CASES, k=RECALL_AT).recall


def _precision() -> float:
    return measure(_searcher(), CASES, k=PRECISION_AT).precision


class TestTheBenchmarkIsWorthRunning:
    def test_there_is_a_corpus_to_search(self):
        assert len(CORPUS) >= 20

    def test_the_ids_are_unique(self):
        assert len({one for one, _ in CORPUS}) == len(CORPUS)

    def test_every_case_points_at_a_document_that_exists(self):
        held = {one for one, _ in CORPUS}
        for case in CASES:
            missing = case.relevant - held
            assert not missing, f"{case.query!r} expects {missing}, not in the corpus"

    def test_there_are_enough_cases_to_average(self):
        assert len(CASES) >= 12

    def test_some_cases_need_more_than_one_document(self):
        assert any(len(case.relevant) > 1 for case in CASES)


class TestTheMeasurementCanFail:
    def test_a_searcher_that_returns_the_wrong_thing_scores_badly(self):
        found = measure(lambda q: ["rotate-logs"], CASES, k=RECALL_AT)
        assert found.recall < FLOOR_RECALL

    def test_a_searcher_that_returns_the_whole_corpus_loses_precision(self):
        everything = [one for one, _ in CORPUS]
        found = measure(lambda q: everything, CASES, k=PRECISION_AT)
        assert found.precision < FLOOR_PRECISION

    def test_returning_everything_does_not_win_recall_either(self):
        everything = [one for one, _ in CORPUS]
        found = measure(lambda q: everything, CASES, k=RECALL_AT)
        assert found.recall < FLOOR_RECALL


class TestTheNumbersDoNotFall:
    def test_recall_holds(self):
        found = _recall()
        assert found >= FLOOR_RECALL, (
            f"recall@{RECALL_AT} fell to {found:.3f} from a floor of "
            f"{FLOOR_RECALL}. Documents that should answer these questions "
            f"stopped coming back. Raise the floor if a change improved it; "
            f"never lower it to make a change pass."
        )

    def test_precision_holds(self):
        found = _precision()
        assert found >= FLOOR_PRECISION, (
            f"precision@{PRECISION_AT} fell to {found:.3f} from a floor of "
            f"{FLOOR_PRECISION}. The top result is wrong more often than it "
            f"was, which is what a change tuned on recall alone does."
        )

    def test_the_precision_floor_is_still_tight(self):
        found = _precision()
        assert found <= FLOOR_PRECISION + 0.1, (
            f"precision@{PRECISION_AT} is {found:.3f}, well above its floor "
            f"of {FLOOR_PRECISION}. Raise the floor so it keeps biting."
        )


class TestTheOneCaseThatMisses:
    """Held onto deliberately rather than relabelled away."""

    def test_it_still_misses(self):
        search = _searcher()
        case = next(
            one for one in CASES if one.query.startswith("why was my request refused")
        )
        top = search(case.query)[:1]
        assert top and top[0] not in case.relevant, (
            "the known miss now hits — if a change fixed it, raise "
            "FLOOR_PRECISION and rewrite this test to say what changed"
        )

    def test_the_right_document_is_at_least_found(self):
        search = _searcher()
        case = next(
            one for one in CASES if one.query.startswith("why was my request refused")
        )
        assert case.relevant & set(search(case.query))
