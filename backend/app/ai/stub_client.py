"""
Deterministic stand-in for the real LLM, used whenever ANTHROPIC_API_KEY is
unset. Lets us build and test the entire interview engine, state machine,
and persistence layer without a live API key or network access - and gives
integration tests a predictable AI to assert against.

Not meant to produce good interview questions - just meant to be honest
about being a stub (see the canned strengths/weaknesses text) and to react
sensibly to answer length/vagueness so the evaluation pipeline is exercised
for real.
"""

from app.ai.stub_resume_extractor import extract_profile_heuristically
from app.interview.vague_detector import detect_vague_flags
from app.schemas.interview import AnswerEvaluation, Difficulty, GeneratedQuestion, Topic
from app.schemas.resume import CandidateProfile

_QUESTION_BANK: dict[Topic, list[tuple[str, list[str]]]] = {
    "dsa": [
        ("Explain the difference between a stack and a queue, and give a real use case for each.", ["stack", "queue"]),
        ("What is the time complexity of binary search, and why does it require a sorted array?", ["binary search", "time complexity"]),
        ("How does a hash table handle collisions?", ["hash table", "collisions"]),
        ("Walk through how you'd detect a cycle in a linked list.", ["linked list", "cycle detection"]),
        ("What's the difference between BFS and DFS, and when would you prefer one over the other?", ["graphs", "bfs", "dfs"]),
    ],
    "oop": [
        ("Explain polymorphism with an example from a project you've built.", ["polymorphism"]),
        ("What's the difference between composition and inheritance?", ["composition", "inheritance"]),
        ("What problem do interfaces/abstract classes solve?", ["abstraction"]),
        ("Explain encapsulation and why it matters in a large codebase.", ["encapsulation"]),
    ],
    "dbms": [
        ("What is database normalization, and what problem does it solve?", ["normalization"]),
        ("Explain the difference between a clustered and non-clustered index.", ["indexing"]),
        ("What are ACID properties, and why do they matter for transactions?", ["acid", "transactions"]),
        ("When would you choose a NoSQL database like MongoDB over a relational database?", ["nosql", "sql", "mongodb"]),
    ],
    "os": [
        ("What is a deadlock, and what are the four necessary conditions for one to occur?", ["deadlock"]),
        ("Explain the difference between a process and a thread.", ["process", "thread"]),
        ("What is virtual memory, and why do operating systems use it?", ["virtual memory"]),
        ("Describe how a round-robin CPU scheduler works.", ["cpu scheduling"]),
    ],
    "cn": [
        ("What happens, step by step, when you type a URL into a browser and hit enter?", ["dns", "tcp", "http"]),
        ("What's the difference between TCP and UDP?", ["tcp", "udp"]),
        ("Explain the three-way handshake in TCP.", ["tcp handshake"]),
        ("What is DNS, and why is it necessary?", ["dns"]),
    ],
}


class StubLLMClient:
    """A fake LLM. Deterministic where possible, so tests can rely on it."""

    async def generate_question(
        self,
        *,
        topic: Topic,
        difficulty: Difficulty,
        previously_asked: list[str],
    ) -> GeneratedQuestion:
        bank = _QUESTION_BANK.get(topic, _QUESTION_BANK["dsa"])
        unused = [q for q in bank if q[0] not in previously_asked]
        question_text, concepts = (unused or bank)[0]

        return GeneratedQuestion(
            question=question_text,
            topic=topic,
            difficulty=difficulty,
            concepts=concepts,
        )

    async def evaluate_answer(
        self,
        *,
        question: str,
        topic: Topic,
        difficulty: Difficulty,
        answer_text: str,
    ) -> AnswerEvaluation:
        vague_flags = detect_vague_flags(answer_text)
        length = len(answer_text.strip())

        # Crude but honest heuristic: longer, non-vague answers score higher.
        # This is NOT a substitute for real evaluation - it exists so the
        # pipeline (scoring, storage, report generation) can be built and
        # tested before a real API key is available.
        if length < 20:
            base = 2
        elif length < 80:
            base = 5
        elif length < 250:
            base = 7
        else:
            base = 8

        penalty = 2 if vague_flags else 0
        score = max(0, min(10, base - penalty))

        return AnswerEvaluation(
            technical_accuracy=score,
            depth=max(0, score - 1) if length < 250 else score,
            completeness=score,
            clarity=score,
            relevance=score,
            communication=score,
            overall=float(score),
            strengths=["Answered without leaving the field blank."] if length > 0 else [],
            weaknesses=(
                ["Answer is vague or under-explained - see flags."]
                if vague_flags
                else (["Could go into more depth."] if score < 7 else [])
            ),
            missing_concepts=[],
            follow_up_recommended=bool(vague_flags) or length < 40,
            follow_up_reason=(
                "Answer relies on unexplained claims." if vague_flags else "Answer is short - worth probing further."
            )
            if (vague_flags or length < 40)
            else "",
            suggested_next_difficulty=(
                "easy" if score < 4 else "hard" if score >= 8 else difficulty
            ),
        )

    async def generate_follow_up_question(
        self,
        *,
        original_question: str,
        original_answer: str,
        topic: Topic,
        difficulty: Difficulty,
        weaknesses: list[str],
        vague_flags: list[str],
    ) -> GeneratedQuestion:
        # Deterministic but genuinely reacts to *why* we're following up,
        # rather than a single canned phrase - so tests (and a human
        # reading stub output) can tell a vague-claim follow-up apart from
        # a too-short-answer follow-up.
        if vague_flags:
            text = (
                "You said that without explaining the mechanism behind it - "
                "what specifically makes that true? Walk me through why."
            )
        else:
            text = "Can you go deeper on that? What would happen at scale, or in an edge case?"

        return GeneratedQuestion(
            question=text,
            topic=topic,
            difficulty=difficulty,
            concepts=[],
        )

    async def extract_candidate_profile(self, *, resume_text: str) -> CandidateProfile:
        return extract_profile_heuristically(resume_text)
