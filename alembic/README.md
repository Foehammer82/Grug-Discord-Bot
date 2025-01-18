# Alembic DB Migrations

## How-To

1. To generate the migration script run `alembic revision --autogenerate -m "{short migration description}"`
2. Make sure to add the generated migration script to your git versioned files
3. To apply the migration run `alembic upgrade head`
