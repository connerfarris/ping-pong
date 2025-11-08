from flask_migrate import Migrate
from ping_pong_web import app, db

migrate = Migrate(app, db)

if __name__ == '__main__':
    with app.app_context():
        # Create migration repository (only needed once)
        # Run: python migrate.py db init
        # Then create a migration: python migrate.py db migrate -m "Initial migration"
        # Apply migrations: python migrate.py db upgrade
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == 'db':
            from flask_migrate import upgrade, migrate as migrate_cmd, init, revision, stamp
            if len(sys.argv) > 2 and sys.argv[2] == 'init':
                init()
            elif len(sys.argv) > 2 and sys.argv[2] == 'migrate':
                message = sys.argv[4] if len(sys.argv) > 4 else 'auto migration'
                migrate_cmd(message=message)
            elif len(sys.argv) > 2 and sys.argv[2] == 'upgrade':
                upgrade()
            elif len(sys.argv) > 2 and sys.argv[2] == 'stamp':
                stamp()
        else:
            print("Usage:")
            print("  Initialize migrations: python migrate.py db init")
            print("  Create migration: python migrate.py db migrate -m 'message'")
            print("  Apply migrations: python migrate.py db upgrade")
            print("  Stamp current DB state: python migrate.py db stamp head")
