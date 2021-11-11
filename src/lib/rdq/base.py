
def _is_resource_not_found(e):
    erc = e.response['Error']['Code']
    return (erc == 'NoSuchEntity') or (erc == 'ResourceNotFoundException')    

def _fail(e, service, op, entityType, entityName, *args):
    print("Unexpected error calling {}:{}".format(service, op))
    print("{}: {}".format(entityType, entityName))
    key = ''
    for a in args:
        if key:
            print("{}: {}".format(key, a))
            key = ''
        else:
            key = a
    if key:
        print(key)
    print(e)
    return "Unexpected error calling {} on {}".format(op, entityName)
