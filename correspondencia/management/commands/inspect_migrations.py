from django.core.management.base import BaseCommand
from django.db.migrations.recorder import MigrationRecorder
from django.apps import apps
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations import CreateModel, AddField, RemoveField, AlterField
import os

class Command(BaseCommand):
    help = "Compara migraciones locales (archivos) con migraciones aplicadas en la base de datos. Añade --analyze para verificar si las operaciones ya existen en la BD."

    def add_arguments(self, parser):
        parser.add_argument('--only-pending', action='store_true', help='Mostrar solo migraciones locales pendientes de aplicar')
        parser.add_argument('--app', help='Limitar el chequeo a una app específica (label)')
        parser.add_argument('--analyze', action='store_true', help='Analizar operaciones pendientes (tabla/campo existe ya en la BD)')

    def _local_migrations(self, app_filter=None):
        local = {}
        for app_config in apps.get_app_configs():
            if app_filter and app_config.label != app_filter:
                continue
            migrations_dir = os.path.join(app_config.path, 'migrations')
            if not os.path.isdir(migrations_dir):
                continue
            names = [f[:-3] for f in os.listdir(migrations_dir) if f.endswith('.py') and f != '__init__.py']
            local[app_config.label] = sorted(names)
        return local

    def _applied_migrations(self):
        applied_qs = MigrationRecorder.Migration.objects.all()
        applied = {}
        for app, name in applied_qs.values_list('app', 'name'):
            applied.setdefault(app, []).append(name)
        return applied

    def _table_exists(self, table_name):
        try:
            tables = connection.introspection.table_names()
            return table_name in tables or table_name.lower() in [t.lower() for t in tables]
        except Exception:
            return False

    def _column_exists(self, table_name, column_name):
        try:
            cols = [c.name for c in connection.introspection.get_table_description(table_name)]
            return column_name in cols or column_name.lower() in [c.lower() for c in cols]
        except Exception:
            return False

    def handle(self, *args, **options):
        only_pending = options['only_pending']
        app_filter = options.get('app')
        analyze = options.get('analyze')

        local = self._local_migrations(app_filter)
        applied = self._applied_migrations()

        if not local:
            self.stdout.write('No se encontraron apps con migraciones locales en la instalación actual.')
            return

        if analyze:
            loader = MigrationLoader(connection)

        total_pending = 0
        for app in sorted(local.keys()):
            local_names = local.get(app, [])
            applied_names = sorted(applied.get(app, []))
            pending = [m for m in local_names if m not in applied_names]
            extra = [m for m in applied_names if m not in local_names]

            if only_pending and not pending:
                continue

            self.stdout.write(f'App: {app}')
            self.stdout.write(f'  Local:   {local_names}')
            self.stdout.write(f'  Applied: {applied_names}')
            self.stdout.write(f'  Pending (local not applied): {pending}')
            self.stdout.write(f'  Extra in DB (applied not local): {extra}')

            if analyze and pending:
                # analizar la primera pending con detalle
                self.stdout.write('  Analizando operaciones de las migraciones pendientes (primas 5):')
                for migration_name in pending[:5]:
                    key = (app, migration_name)
                    mig = loader.disk_migrations.get(key)
                    if not mig:
                        self.stdout.write(f'    - No se encontró el objeto migración en disco para {migration_name}')
                        continue
                    self.stdout.write(f'    - Migration: {migration_name}')
                    for op in mig.operations:
                        if isinstance(op, CreateModel):
                            model = op.name
                            table = op.options.get('db_table') or f"{app}_{model.lower()}"
                            exists = self._table_exists(table)
                            self.stdout.write(f"      CreateModel {model} -> table '{table}' exists: {exists}")
                        elif isinstance(op, AddField):
                            model = op.model_name
                            field = op.name
                            table = f"{app}_{model.lower()}"
                            table_exists = self._table_exists(table)
                            field_exists = self._column_exists(table, field) if table_exists else False
                            self.stdout.write(f"      AddField {model}.{field} -> table '{table}' exists: {table_exists}, column exists: {field_exists}")
                        elif isinstance(op, RemoveField):
                            model = op.model_name
                            field = op.name
                            table = f"{app}_{model.lower()}"
                            table_exists = self._table_exists(table)
                            field_exists = self._column_exists(table, field) if table_exists else False
                            self.stdout.write(f"      RemoveField {model}.{field} -> table '{table}' exists: {table_exists}, column exists (now): {field_exists}")
                        elif isinstance(op, AlterField):
                            model = op.model_name
                            field = op.name
                            table = f"{app}_{model.lower()}"
                            field_exists = self._column_exists(table, field)
                            self.stdout.write(f"      AlterField {model}.{field} -> column exists: {field_exists}")
                        else:
                            self.stdout.write(f"      Op manual/no chequeada: {op.__class__.__name__}")
            self.stdout.write('')

            total_pending += len(pending)

        self.stdout.write(f'Total pending migrations: {total_pending}')

