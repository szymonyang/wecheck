default:
	python manage.py runserver

clean:
	rm db.sqlite3
	python manage.py migrate
