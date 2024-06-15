from collections import OrderedDict


databases = {
    "postgresql": OrderedDict(
        user={
            'type': 'string',
            'description': 'The user name used to authenticate with the PostgreSQL server.',
            'required': True,
            'label': 'User'
        },
        password={
            'type': 'password',
            'description': 'The password to authenticate the user with the PostgreSQL server.',
            'required': True,
            'label': 'Password',
            'secret': True
        },
        database={
            'type': 'string',
            'description': 'The database name to use when connecting with the PostgreSQL server.',
            'required': True,
            'label': 'Database'
        },
        host={
            'type': 'string',
            'description': 'The host name or IP address of the PostgreSQL server.',
            'required': True,
            'label': 'Host'
        },
        port={
            'type': 'number',
            'description': 'The TCP/IP port of the PostgreSQL server. Must be an integer.',
            'required': True,
            'label': 'Port'
        }
    )
}