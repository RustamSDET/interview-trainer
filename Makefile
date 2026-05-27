.PHONY: run seed seed-fresh

run:
	.venv/bin/streamlit run src/web/app.py --server.port 8502

seed:
	.venv/bin/python src/database/seed.py

seed-fresh:
	.venv/bin/python src/database/seed.py --fresh
