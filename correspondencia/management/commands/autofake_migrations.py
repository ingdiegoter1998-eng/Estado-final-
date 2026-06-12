from django.core.management.base import BaseCommand
from django.db.migrations.recorder import MigrationRecorder
from django.apps import apps
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations import CreateModel, AddField, RemoveField, AlterField
import os

class Command(BaseCommand):
    help = (
        "Detecta migraciones seguras para marcar como aplicadas (fake). "
        "Usa --dry-run para listar candidatos, --apply para ejecutar fakes." 
    )

    def add_arguments(self, parser):
        parser.add_argument('--apps', nargs='*', help='Lista de apps a procesar (por defecto: todas con pendientes)')
        parser.add_argument('--dry-run', action='store_true', help='Mostrar qué migraciones serían marcadas sin aplicar nada')
        parser.add_argument('--apply', action='store_true', help='Marcar (fake) las migraciones consideradas seguras')
        parser.add_argument('--yes', action='store_true', help='Confirmar automáticamente el apply')

    def _local_migrations(self, app_filter=None):
        local = {}
        for app_config in apps.get_app_configs():
            if app_filter and app_config.label not in app_filter:
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
        apps_arg = options.get('apps')
        dry_run = options['dry_run']
        do_apply = options['apply']
        auto_yes = options['yes']

        applied = self._applied_migrations()
        local = self._local_migrations(apps_arg)

        loader = MigrationLoader(connection)

        candidates = []
        unsafe = []

        for app, local_names in sorted(local.items()):
            applied_names = set(applied.get(app, []))
            pending = [m for m in local_names if m not in applied_names]
            if not pending:
                continue

            for mig_name in pending:
                key = (app, mig_name)
                mig = loader.disk_migrations.get(key)
                if not mig:
                    unsafe.append((app, mig_name, 'no_disk_migration'))
                    continue
                safe_ops = True
                reasons = []
                for op in mig.operations:
                    if isinstance(op, CreateModel):
                        model = op.name
                        table = op.options.get('db_table') or f"{app}_{model.lower()}"
                        if not self._table_exists(table):
                            # CreateModel and table doesn't exist -> applying would be destructive to mark fake
                            safe_ops = False
                            reasons.append(f"CreateModel {model}: table '{table}' missing")
                    elif isinstance(op, AddField):
                        model = op.model_name
                        field = op.name
                        table = f"{app}_{model.lower()}"
                        if not self._table_exists(table):
                            safe_ops = False
                            reasons.append(f"AddField {model}.{field}: table '{table}' missing")
                        else:
                            # if column already exists, safe to fake
                            if not self._column_exists(table, field):
                                safe_ops = False
                                reasons.append(f"AddField {model}.{field}: column missing in '{table}'")
                    elif isinstance(op, RemoveField):
                        model = op.model_name
                        field = op.name
                        table = f"{app}_{model.lower()}"
                        # if column already missing, safe to fake
                        if self._table_exists(table) and self._column_exists(table, field):
                            safe_ops = False
                            reasons.append(f"RemoveField {model}.{field}: column still present in '{table}'")
                    elif isinstance(op, AlterField):
                        # Conservative: altering fields can be unsafe -> mark unsafe
                        model = op.model_name
                        field = op.name
                        reasons.append(f"AlterField {model}.{field}: marked potentially unsafe")
                        safe_ops = False
                    else:
                        reasons.append(f"Op {op.__class__.__name__}: unknown/unsafe")
                        safe_ops = False

                if safe_ops:
                    candidates.append((app, mig_name))
                else:
                    unsafe.append((app, mig_name, '; '.join(reasons)))

        # Output dry-run summary
        if dry_run or not do_apply:
            self.stdout.write('--- DRY RUN: migrations that would be FAKED ---')
            for app, mig in candidates:
                self.stdout.write(f'  - {app}.{mig}')
            self.stdout.write('')
            self.stdout.write('--- MIGRATIONS MARKED UNSAFE (no tocar automáticamente) ---')
            for app, mig, reason in unsafe:
                self.stdout.write(f'  - {app}.{mig} -> {reason}')
            self.stdout.write('')
            self.stdout.write(f'Total candidates to fake: {len(candidates)}')

        # Apply if requested
        if do_apply:
            if not candidates:
                self.stdout.write('No candidates para aplicar.')
                return
            if not auto_yes:
                confirm = input(f"Confirmar marcar {len(candidates)} migraciones como aplicadas? (type 'yes' to proceed): ")
                if confirm.strip().lower() != 'yes':
                    self.stdout.write('Aborted by user')
                    return
            # Apply fakes
            for app, mig in candidates:
                self.stdout.write(f'Applying fake: {app}.{mig}')
                os.system(f'venv/bin/python manage.py migrate {app} {mig} --fake')
            self.stdout.write('Aplicación completa. Ejecuta inspect_migrations de nuevo para verificar.')
