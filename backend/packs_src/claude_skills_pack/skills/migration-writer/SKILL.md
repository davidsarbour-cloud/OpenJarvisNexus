---
name: migration-writer
description: Write a database migration (schema change) matching the project's migration tool. Use to add/alter tables or /migration-writer.
argument-hint: "<the schema change you want>"
---

Write a DB migration for the change in $ARGUMENTS (ask if empty).

1. Detect the migration tool and conventions: Prisma, Knex, TypeORM, Alembic, Django, Rails, Flyway, golang-migrate, etc. Look at existing migrations to match naming, format, and location.
2. Write the migration with BOTH directions where the tool supports it: an `up` (apply) and a `down` (rollback) that cleanly reverses it.
3. Make it safe: for production tables, prefer additive/backfill-friendly steps (add nullable column → backfill → add constraint) over a single locking change; call out anything that could lock a large table or lose data.
4. Update the schema/model file too if the tool keeps one (Prisma schema, Django models, entities).
5. Show the generate/run command for the tool (e.g. `prisma migrate dev`, `alembic upgrade head`) but don't run it against a real database unless the user asks. Flag any destructive step (DROP, NOT NULL on existing data) explicitly.
