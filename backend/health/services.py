from django.db import models


class HealthStatus(models.TextChoices):
    OK = "ok"


def do_health_check() -> dict[str, HealthStatus]:
    """Run a trivial query against the database and return `{"status": "ok"}`.

    A database failure is not caught here: it propagates to the exception handler, which logs it
    and returns a 500.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return {"status": HealthStatus.OK}
