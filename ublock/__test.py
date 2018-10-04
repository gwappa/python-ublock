from traceback import print_exc

"""snippets for testing result parsing."""

status = ('hit', 'miss', 'catch', 'reject')
values = ('wait', 'visual')
arrays = ('whisk', 'lick')

def parseSingle(token):
    print(f"token({token})")
    token = token.strip()
    for s in status:
        if token == s:
            print(f"status: {s}")
            return
    for val in values:
        try:
            if token.startswith(val):
                arg = int(token[len(val):])
                print(f"value: {val} = {arg}")
                return
        except ValueError:
            print_exc()
            print("***error while parsing value '{}': {}".format(val, token))
            return
    for arr in arrays:
        try:
            if token.startswith(arr):
                arg = token[len(arr):]
                if (arg[0] != '[') or (arg[-1] != ']'):
                    continue
                args = arg[1:-1].split(',')
                arglist = []
                for elem in args:
                    arglist.append(int(elem))
                print(f"array: {arr} = {arglist}")
                return
        except ValueError:
            print_exc()
            print("***error while parsing array '{}': {}".format(val, arg))
            return
    # no match
    print(f"unknown: {token}")

def parse(line):
    print(f"line({line})")
    tokens = line[1:].split(';')
    for token in tokens:
        parseSingle(token) 
    print("done")
    
