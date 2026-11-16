from django.db import migrations


def add_steadfast_source(apps, schema_editor):
    source = apps.get_model('app', 'IntegrationSource')
    source.objects.using(schema_editor.connection.alias).get_or_create(
        key='steadfast', defaults={'name': 'Steadfast', 'category': 'COURIER',
                                   'connection_type': 'API_KEY',
                                   'description': 'Steadfast courier shipments and tracking'})


def remove_steadfast_source(apps, schema_editor):
    # Existing connections may reference the source; leave it in place on rollback.
    pass


class Migration(migrations.Migration):
    dependencies = [('app', '0010_alter_integrationsynclog_created_at')]
    operations = [migrations.RunPython(add_steadfast_source, remove_steadfast_source)]
