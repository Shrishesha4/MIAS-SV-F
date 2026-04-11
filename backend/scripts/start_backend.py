import asyncio
import os
import sys

from app.db_init import run_startup_migrations


def main() -> None:
	asyncio.run(run_startup_migrations())
	os.execvp(
		'gunicorn',
		[
			'gunicorn',
			'app.main:app',
			'-w',
			'4',
			'-k',
			'uvicorn.workers.UvicornWorker',
			'--bind',
			'0.0.0.0:8000',
			'--access-logfile',
			'-',
			'--error-logfile',
			'-',
		],
	)


if __name__ == '__main__':
	try:
		main()
	except Exception:
		import traceback

		traceback.print_exc()
		sys.exit(1)