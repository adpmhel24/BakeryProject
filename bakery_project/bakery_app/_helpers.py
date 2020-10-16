import datetime
from flask.json import JSONEncoder
from decimal import Decimal
from sqlalchemy import and_, or_

class fakefloat(float):
    def __init__(self, value):
        self._value = value
    def __repr__(self):
        return str(self._value)
        
class CustomJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            # Subclass float with custom repr?
            return fakefloat(o)
        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()
        raise TypeError(repr(o) + " is not JSON serializable")


dict_filtros_op = {
    '==':'eq',
    '!=':'ne',
    '>':'gt',
    '<':'lt',
    '>=':'ge',
    '<=':'le',
    'like':'like',
    'ilike':'ilike',
    'in':'in'
}


class BaseDao():
    @classmethod
    # @init_db_connection
    def create_query_select(cls, model, filters=None, columns=None):
        return cls.db_session.query(*cls.create_query_columns(model=model, columns=columns))\
            .filter(*cls.create_query_filter(model=model, filters=filters))

    @classmethod
    def create_query_filter(cls, model, filters):
        '''
        return sqlalchemy filter list
        Args:
            model:sqlalchemy  model (classe das tabelas)
            filters: filter dict
                     ex:
                        filters = {
                            'or_1':{
                                'and_1':[('id', '>', 5),('id', '!=', 3)],
                                'and_2':[('fase', '==', 'arquivado')]
                            },
                            'and':[('test', '==', 'test')]
                        }
        Returns:
            filt: sqlalchemy filter list
         '''
        if not filters:
            return []

        filt = []
        for condition in filters:
            if type(filters[condition]) == dict:
                if 'and' in condition:
                    filt.append(and_(*cls.create_query_filter(model, filters[condition])))
                elif 'or' in condition:
                    filt.append(or_(*cls.create_query_filter(model, filters[condition])))
                else:
                    raise Exception('Invalid filter condition: %s' % condition)
                continue
            filt_aux = []
            for t_filter in filters[condition]:
                try:
                    column_name, op, value = t_filter
                except ValueError:
                    raise Exception('Invalid filter: %s' % t_filter)
                if not op in dict_filtros_op:
                    raise Exception('Invalid filter operation: %s' % op)
                column = getattr(model, column_name, None)
                if not column:
                    raise Exception('Invalid filter column: %s' % column_name)
                if dict_filtros_op[op] == 'in':
                    filt.append(column.in_(value))
                else:
                    try:
                        attr = list(filter(lambda e: hasattr(column, e % dict_filtros_op[op]), ['%s', '%s_', '__%s__']))[0] % dict_filtros_op[op]
                    except IndexError:
                        raise Exception('Invalid filter operator: %s' % dict_filtros_op[op])
                    if value == 'null':
                        value = None
                    filt_aux.append(getattr(column, attr)(value))
            if 'and' in condition:
                filt.append(and_(*filt_aux))
            elif 'or' in condition:
                filt.append(or_(*filt_aux))
            else:
                raise Exception('Invalid filter condition: %s' % condition)
        return filt

    @classmethod
    def create_query_columns(cls, model, columns):
        '''
        Return a list of attributes (columns) from the class model
        Args:
            model: sqlalchemy model
            columns: string list
                     ex: ['id', 'cnj']
        Returns:
            cols: list of attributes from the class model
         '''
        if not columns:
            return [model]

        cols = []
        for column in columns:
            attr = getattr(model, column, None)
            if not attr:
                raise Exception('Invalid column name %s' % column)
            cols.append(attr)
        return cols