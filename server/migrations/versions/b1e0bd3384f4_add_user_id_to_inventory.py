from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1e0bd3384f4'
down_revision = 'e75bdc0c6ad2'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('inventory', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_inventory_user_id', 'users', ['user_id'], ['id'])

    # Set default value for existing records, you might want to change this
    op.execute('UPDATE inventory SET user_id = (SELECT id FROM users LIMIT 1)')

    # Now make the column non-nullable
    with op.batch_alter_table('inventory', schema=None) as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=False)

def downgrade():
    with op.batch_alter_table('inventory', schema=None) as batch_op:
        batch_op.drop_constraint('fk_inventory_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')
