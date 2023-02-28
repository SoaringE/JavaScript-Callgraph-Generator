import matplotlib.pyplot as plt
import networkx as nx
import getScript as get
import sys


symbols = set("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
operators = ('+', '-', '*', '/', '%', '=', '.', '>', '<', '&', '|', '!',
             '+=', '-=', '++', '--', '**', '*=', '/=', '>=', '<=', '==', '!=',
             '===', '!==', '&&', '||', '&&=', '||=', '&=', '|=', '~', '^',
             '>>', '>>>', '<<', '^=', '>>=', '>>>=', '<<=', '=>')
punctuations = (';', ',', ':', '{', '}', '(', ')', '\"', '\'')

tokens = []
remain = []
classes = {}
functions = {}
callEdges = []


class Variable:
    def __init__(self, name):
        self.name = name


class Instance:
    def __init__(self, jtype):
        self.type = jtype


class Invoke:
    def __init__(self, recv, name, args):
        self.recv = recv
        self.name = name
        self.args = args


class Class:
    def __init__(self, name, parent, attrs, methods):
        self.name = name
        self.parent = parent
        self.attrs = attrs
        self.methods = methods


def rightExp(s: str, piece, env):
    if s[0] in ('"', "'", '`') and len(piece) == 1:
        return Instance('string')
    if s.isdigit() or all(list(map(lambda x: x.isdigit(), s.split('.')))):
        return Instance('number')
    if s == 'true' or s == 'false':
        return Instance('boolean')
    if len(piece) == 1:
        return Instance(env[s])
    if '=>' in piece:
        paras = []
        boundary = piece.index('=>')
        for j in range(0, boundary):
            if piece[j] not in (',', '(', ')'):
                paras.append(piece[j])
        content = ['return']
        for j in range(boundary + 1, len(piece)):
            content.append(piece[j])
        return Function('lambda: ' + s, paras, content)
    if piece[1] in operators and piece[1] != '.' and piece[1] != '(':
        left = rightExp(piece[0], [piece[0]], env)
        right = rightExp(piece[2], [piece[2]], env)
        if isinstance(left, Instance) and isinstance(right, Instance):
            if left.type == 'string' or right.type == 'string':
                return Instance('string')
            return Instance('number')
        elif isinstance(left, Instance) and not isinstance(right, Instance):
            if env[piece[2]] != 'unknown':
                if left.type == 'string' or env[piece[2]] == 'string':
                    return Instance('string')
                return Instance('number')
        elif not isinstance(left, Instance) and isinstance(right, Instance):
            if env[piece[0]] != 'unknown':
                if right.type == 'string' or env[piece[0]] == 'string':
                    return Instance('string')
                return Instance('number')
        else:
            if env[piece[0]] != 'unknown' and env[piece[2]] != 'unknown':
                if env[piece[0]] == 'string' or env[piece[2]] == 'string':
                    return Instance('string')
                return Instance('number')
    if piece[0] == 'new':
        return Instance(piece[1])
    if piece[1] == '.':
        if len(piece) == 3:
            return Variable(s)
        else:
            args = []
            for j in range(4, len(piece)):
                if piece[j] == ')':
                    break
                if piece[j] == ',':
                    continue
                else:
                    args.append(piece[j])
            return Invoke(piece[0], (env.get(piece[0], piece[0]) if
                                     env.get(piece[0], piece[0]) != 'unknown' else
                                     piece[0]) + '.' + piece[2], args)
    if piece[1] == '(':
        args = []
        for j in range(2, len(piece)):
            if piece[j] == ')':
                break
            if piece[j] == ',':
                continue
            else:
                args.append(piece[j])
        return Invoke(None, piece[0], args)
    return None


class Function:
    def __init__(self, name, parameters, content):
        self.name = name
        self.parameters = parameters
        self.content = content
        self.env = {}
        self.returnType = 'void'

    def analyze(self, stmts):
        temp = []
        i, length = 0, len(stmts)
        while i < length:
            if stmts[i] == 'if' or stmts[i] == 'while':
                depth = 0
                j = i + 1
                while j < length:
                    if stmts[j] == '(':
                        depth += 1
                    elif stmts[j] == ')':
                        depth -= 1
                        if depth == 0:
                            j += 1
                            break
                    j += 1
                i = j
            elif stmts[i] not in ('else', '{', '}'):
                temp.append(stmts[i])
                i += 1
            else:
                i += 1
        stmts, inner = [], []
        for token in temp:
            if token == ';':
                stmts.append(inner)
                inner = []
            else:
                inner.append(token)
        i, length = 0, len(stmts)
        while i < length:
            if stmts[i][0] in ('var', 'let', 'const'):
                varName = stmts[i][1]
                if len(stmts[i]) == 2:
                    self.env[varName] = 'unknown'
                    i += 1
                else:
                    piece = stmts[i][3:]
                    right = rightExp(''.join(piece), piece, self.env)
                    self.env[varName] = 'unknown' if not isinstance(right, Instance) else right.type
                    if isinstance(right, Function):
                        self.env[varName] = 'function'
                        functions[varName] = right
                    if isinstance(right, Instance):
                        if right.type in classes.keys() and piece[0] == 'new':
                            callee: Function = functions[right.type + '.constructor']
                            args = []
                            for j in range(3, len(piece)):
                                if piece[j] == ')':
                                    break
                                if piece[j] == ',':
                                    continue
                                else:
                                    args.append(piece[j])
                            for arg, param in zip(args, callee.parameters):
                                callee.env[param] = rightExp(arg, [arg], self.env).type
                            callee.analyze(callee.content)
                            callEdges.append([self, callee])
                    if isinstance(right, Invoke):
                        if right.name in functions.keys():
                            callee = functions[right.name]
                            for arg, param in zip(right.args, callee.parameters):
                                callee.env[param] = rightExp(arg, [arg], self.env).type
                            if self is not callee:
                                callee.analyze(callee.content)
                            self.env[varName] = 'unknown' if callee.returnType == 'void' else callee.returnType
                            callEdges.append([self, callee])
                        else:
                            callEdges.append([self, right.name])
                    i += 1
            elif '=' in stmts[i]:
                j = 0
                while j < len(stmts[i]):
                    if stmts[i][j] == '=':
                        break
                    j += 1
                piece = stmts[i][j + 1:]
                left = ''.join(stmts[i][: j])
                right = rightExp(''.join(piece), piece, self.env)
                self.env[left] = 'unknown' if not isinstance(right, Instance) else right.type
                if isinstance(right, Instance):
                    if right.type in classes.keys():
                        callee: Function = functions[right.type + '.constructor']
                        args = []
                        for j in range(3, len(piece)):
                            if piece[j] == ')':
                                break
                            if piece[j] == ',':
                                continue
                            else:
                                args.append(piece[j])
                        for arg, param in zip(args, callee.parameters):
                            callee.env[param] = rightExp(arg, [arg], self.env).type
                        callee.analyze(callee.content)
                        callEdges.append([self, callee])
                if isinstance(right, Invoke):
                    if right.name in functions.keys():
                        callee = functions[right.name]
                        for arg, param in zip(right.args, callee.parameters):
                            callee.env[param] = rightExp(arg, [arg], self.env).type
                        if self is not callee:
                            callee.analyze(callee.content)
                        self.env[left] = 'unknown' if callee.returnType == 'void' else callee.returnType
                        callEdges.append([self, callee])
                    else:
                        callEdges.append([self, right.name])
                i += 1
            elif stmts[i][0] == 'return':
                if len(stmts[i]) > 1:
                    piece = stmts[i][1:]
                    right = rightExp(''.join(piece), piece, self.env)
                    if not isinstance(right, Invoke):
                        self.returnType = 'void' if not isinstance(right, Instance) else right.type
                i += 1
            else:
                piece = stmts[i]
                right = rightExp(''.join(piece), piece, self.env)
                if isinstance(right, Invoke):
                    if right.name in functions.keys():
                        callee = functions[right.name]
                        for arg, param in zip(right.args, callee.parameters):
                            callee.env[param] = rightExp(arg, [arg], self.env).type
                        if self is not callee:
                            callee.analyze(callee.content)
                        callEdges.append([self, callee])
                    elif right.name == 'super':
                        parent: Class = classes[classes[self.name.split('.')[0]].parent]
                        callEdges.append([self, functions[parent.name + '.' + 'constructor']])
                    else:
                        callEdges.append([self, right.name])
                i += 1


def tokenize(script):
    i, length = 0, len(script)
    while i < length:
        if script[i] == ' ' or script[i] == '\n' or script[i] == '\t':
            i += 1
        elif script[i] in symbols and not script[i].isdigit():
            temp = ''
            j = i
            while j < length:
                if script[j] not in symbols:
                    break
                temp += script[j]
                j += 1
            tokens.append(temp)
            i = j
        elif script[i].isdigit():
            temp = ''
            j = i
            while j < length:
                if not script[j].isdigit():
                    break
                temp += script[j]
                j += 1
            if len(tokens) > 2 and tokens[-1] == '.' and tokens[-2].isdigit():
                tokens[-2] += '.' + temp
                tokens.pop()
            else:
                tokens.append(temp)
            i = j
        else:
            if script[i] in operators and tokens[-1] in operators and script[i] + tokens[-1] in operators:
                tokens[-1] += script[i]
                i += 1
            elif script[i] == '\"':
                temp = ''
                j = i
                while j < length:
                    temp += script[j]
                    j += 1
                    if script[j] == '\"':
                        temp += script[j]
                        j += 1
                        break
                tokens.append(temp)
                i = j
            elif script[i] == '\'':
                temp = ''
                j = i
                while j < length:
                    temp += script[j]
                    j += 1
                    if script[j] == '\'':
                        temp += script[j]
                        j += 1
                        break
                tokens.append(temp)
                i = j
            elif script[i] == '`':
                temp = ''
                j = i
                while j < length:
                    temp += script[j]
                    j += 1
                    if script[j] == '`':
                        temp += script[j]
                        j += 1
                        break
                tokens.append(temp)
                i = j
            else:
                tokens.append(script[i])
                i += 1


def analyze():
    i, length = 0, len(tokens)
    while i < length:
        if tokens[i] == 'class':
            className, methodName, parent, attrs, methods, stmts = '', '', '', [], [], []
            constructing, buildingMethod = False, False
            parameters = []
            braceDepth = 0
            j = i
            while j < length:
                if j == i + 1:
                    className = tokens[j]
                elif j == i + 2 and tokens[j] == 'extends':
                    parent = tokens[j + 1]
                elif tokens[j] == '{':
                    braceDepth += 1
                elif tokens[j] == '}':
                    braceDepth -= 1
                    if braceDepth == 1:
                        if constructing:
                            constructing = False
                            func = Function(className + '.' + 'constructor', parameters, stmts)
                            methods.append(func)
                            functions[className + '.' + 'constructor'] = func
                        if buildingMethod:
                            buildingMethod = False
                            func = Function(className + '.' + methodName, parameters, stmts)
                            methods.append(func)
                            functions[className + '.' + methodName] = func
                        parameters = []
                        stmts = []
                    if braceDepth == 0:
                        # start comparing with parent
                        if parent != '':
                            parentClass: Class = classes[parent]
                            for attr in parentClass.attrs:
                                if attr not in attrs:
                                    attrs.append(attr)
                            for method in parentClass.methods:
                                if method.name.split('.')[1] not in list(map(lambda m: m.name.split('.')[1], methods)):
                                    f = Function(className + '.' + method.name.split('.')[1],
                                                 method.parameters, method.content)
                                    methods.append(f)
                                    functions[f.name] = f
                        classes[className] = Class(className, parent, attrs, methods)
                        i = j + 1
                        break
                elif braceDepth == 1:
                    if not constructing and not buildingMethod and tokens[j] == 'constructor':
                        constructing = True
                    elif not constructing and not buildingMethod and tokens[j].isalpha():
                        buildingMethod = True
                        methodName = tokens[j]
                    elif constructing:
                        if tokens[j].isalpha():
                            parameters.append(tokens[j])
                    elif buildingMethod:
                        if tokens[j].isalpha():
                            parameters.append(tokens[j])
                elif braceDepth == 2:
                    stmts.append(tokens[j])
                    if constructing:
                        if tokens[j] == 'this':
                            attrs.append(tokens[j + 2])
                j += 1

        elif tokens[i] == 'function':
            """
            function abs(x) {
                if (x >= 0) {
                    return x;
                } else {
                    return -x;
                }
            }
            """
            funcName, parameters, stmts = tokens[i + 1], [], []
            j = i + 3
            while j < length:
                if tokens[j].isalpha():
                    parameters.append(tokens[j])
                else:
                    if tokens[j] == '{':
                        break
                j += 1
            braceDepth = 0
            while j < length:
                if braceDepth > 0:
                    stmts.append(tokens[j])
                if tokens[j] == '{':
                    braceDepth += 1
                if tokens[j] == '}':
                    braceDepth -= 1
                    if braceDepth == 0:
                        stmts.pop()
                        functions[funcName] = Function(funcName, parameters, stmts)
                        break
                j += 1
            i = j + 1
        else:
            remain.append(tokens[i])
            i += 1


def build(entry):
    program_entry = Function(entry, [], remain)
    program_entry.env['this'] = 'Window'
    program_entry.env['window'] = 'Window'
    program_entry.analyze(program_entry.content)


def draw():
    graph = nx.MultiDiGraph()
    for edge in callEdges:
        graph.add_edge(edge[0].name, edge[1].name if isinstance(edge[1], Function) else edge[1])
    nx.draw_planar(graph, with_labels=True)
    plt.show()


def initialize():
    global tokens, remain, classes, functions, callEdges
    tokens = []
    remain = []
    classes = {}
    functions = {}
    callEdges = []


def main():
    link = ''
    if len(sys.argv) >= 2:
        link = sys.argv[1]
    else:
        exit(-1)
    scripts, entries = get.fetch(link)
    for key, value in entries:
        initialize()
        tokenize(scripts + value)
        analyze()
        build(key)
        draw()


main()
