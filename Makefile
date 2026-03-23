.PHONY: dev backend frontend install

install:
	cd /Users/lichenyu/compliance-os && pip install -e ".[dev]"
	cd /Users/lichenyu/compliance-os/frontend && npm install

backend:
	cd /Users/lichenyu/compliance-os && uvicorn compliance_os.web.app:app --reload --port 8000

frontend:
	cd /Users/lichenyu/compliance-os/frontend && npm run dev

dev:
	@echo "Starting backend and frontend..."
	@make backend & make frontend & wait
