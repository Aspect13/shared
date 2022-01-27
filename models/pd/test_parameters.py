from typing import Optional, Any, List, get_origin
from pydantic import BaseModel, validator, AnyUrl, parse_obj_as


class TestParameter(BaseModel):
    class Config:
        anystr_strip_whitespace = True
        anystr_lower = True

    __type_mapping = {
        'url': AnyUrl,
        'urls': List[AnyUrl],
        'string': str,
        'number': int,
        'list': list,
        'item': str
    }
    _type_mapping_by_name = dict()
    _required_params = set()

    name: str
    type: Optional[str] = 'string'
    description: Optional[str] = ''
    default: Optional[Any] = ''

    @classmethod
    def get_real_type(cls, type_: str, name: str) -> type:
        if isinstance(type_, type):
            return type_
        if cls._type_mapping_by_name.get(name):
            return cls._type_mapping_by_name.get(name)
        elif cls.__type_mapping.get(type_):
            return cls.__type_mapping.get(type_)
        return str

    # @validator('type')
    # def validate_type(cls, value, values):
    #     return cls.get_real_type(
    #         value,
    #         values.get('name')
    #     )

    @validator('default')
    def convert_default_type(cls, value, values):
        real_type = cls.get_real_type(
            values.get('type'),
            values.get('name')
        )
        value = cls.convert_types(value, real_type)
        return parse_obj_as(Optional[real_type], value)

    @staticmethod
    def convert_types(value, _type, list_delimiter=','):
        _checked_type = get_origin(_type) or _type
        if value is not None:
            if isinstance(value, str):
                value = value.strip()
            if not isinstance(value, list) and _checked_type is list:
                value = [i.strip() for i in str(value).split(list_delimiter)]
            elif isinstance(value, list) and _checked_type is not list:
                value = list_delimiter.join(value)
        return value
