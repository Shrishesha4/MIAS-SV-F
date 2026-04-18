import asyncio
import os
import sys

from app.db_init import run_startup_migrations


def main() -> None:
	asyncio.run(run_startup_migrations())
	# (2×CPU)+1 formula. WEB_CONCURRENCY env overrides for per-host tuning.
	# 20-core prod: WEB_CONCURRENCY=41. Dev default: 9.
	workers = os.environ.get("WEB_CONCURRENCY", str((os.cpu_count() or 4) * 2 + 1))
	os.execvp(
		'gunicorn',
		[
			'gunicorn',
			'app.main:app',
			'-w', workers,
			'-k', 'uvicorn.workers.UvicornWorker',
			'--bind', '0.0.0.0:8000',
			# Share loaded code across workers via copy-on-write — saves ~4GB RAM on 41 workers
			'--preload',
			# 2 threads per worker: rare sync calls don't block the event loop
			'--threads', '2',
			'--worker-connections', '2000',
			'--timeout', '60',
			'--graceful-timeout', '30',
			'--keep-alive', '5',
			# Recycle workers every 10k requests to prevent memory bloat
			'--max-requests', '10000',
			'--max-requests-jitter', '1000',
			'--access-logfile', '-',
			'--error-logfile', '-',
		],
	)


if __name__ == '__main__':
	try:
		main()
	except Exception:
		import traceback

		traceback.print_exc()
		sys.exit(1)