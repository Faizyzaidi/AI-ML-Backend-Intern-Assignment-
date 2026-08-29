# Knowledge Base Source Documents

Place role-specific PDFs (or .txt files) here, one subfolder per role slug:

```
knowledge_base/
  ai-ml-engineer/
    machine-learning-tom-mitchell.pdf
    hundred-page-ml-book.pdf
  data-science/
    intro-to-ml-with-python.pdf
    master-ml-algorithms-brownlee.pdf
  backend-engineer/
    your-backend-reference.pdf
```

The role slug (the folder name) becomes the value the frontend's role
selector should send to `POST /api/session/start`, and is what a Chroma
collection gets named after (`role_<slug>`).

After adding files, run the ingestion pipeline from `backend/`:

```bash
python -m app.rag.ingest                 # ingest every role folder
python -m app.rag.ingest --role ai-ml-engineer   # ingest just one role
```

See section 9 of the assignment brief for suggested source books per role
(e.g., *Machine Learning* — Tom Mitchell; *The Hundred-Page Machine
Learning Book* — Andriy Burkov; *Introduction to Machine Learning with
Python*).
