from bakery_app import create_app
from bakery_app import db
from flask_script import Manager, Server
from flask_migrate import Migrate, MigrateCommand

app = create_app()
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)
manager.add_command("runserver", Server())

if __name__ == '__main__':
    manager.run()
