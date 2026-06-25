> *_Work in Progress!_*

# Spottr 🏋️

> An AI lifting coach — a spotter for your training data.

Spottr is a local-first, Dockerized backend that lets you log your workouts and then *talk
to your training history* in plain English. Ask it "How's my squat trending?" and it queries
your actual data. Ask it "Should I deload?" and it answers using a corpus of strength-training
knowledge — with citations back to the source.

It combines two AI techniques under one clean API:
- **Tool-calling** over your structured workout data, so answers are grounded in your real
  numbers instead of hallucinated.
- **Retrieval-Augmented Generation (RAG)** over a coaching-knowledge corpus, so advice is
  grounded in real training principles and cited.

---

## Why this exists

Most training logs are just databases with a UI. Spottr adds a reasoning layer: it decides
whether a question needs *your data*, *coaching knowledge*, or *both*, fetches what it needs,
and synthesizes a personalized, cited answer.

It's also a portfolio project demonstrating practical AI application engineering: REST APIs,
structured/unstructured JSON processing, LLM tool-calling, RAG with a vector database,
containerization, and an evaluation harness.

---

## Features

- 📓 **Workout logging** — sets, reps, weight, RPE, bodyweight, notes.
- 📈 **Natural-language analytics** — "What's my bench e1RM trend over 12 weeks?" answered
  from your real data via LLM tool-calling.
- 📚 **Cited coaching Q&A** — ingest training articles and guides; ask questions and get
  answers grounded in retrieved passages with source citations.
- 🔀 **Hybrid answers** — questions like "Given my recent volume, should I deload?" combine
  your data *and* coaching principles in one response.
- ✅ **Evaluation harness** — automated checks for tool-use accuracy and retrieval quality.
- 🐳 **Fully Dockerized** — `docker compose up` and you're running.

---
## License

MIT
