from semantics import Semantics, Relation, Variable, Constant

class SemanticParser(object):
    @classmethod
    def parse(cls, string):
        """Returns a Semantic object"""
        string = string.replace(" ", "")
        relations = []
        while len(string) > 0:
            relation, string = RelationParser.parse(string)
            relations.append(relation)
        return Semantics(relations)


class RelationParser(object):
    @classmethod
    def parse(cls, string):
        relname, rest = string.split("(", 1)
        args = []
        while(rest[0] != ")"):
            arg, rest = VariableParser.parse(rest)
            args.append(arg)

        rest = rest[1:] # Remove ")"
        if len(rest) > 0 and rest[0] == ",":
            rest = rest[1:] # Remove ","

        return Relation(relname, args), rest

class VariableParser(object):
    @classmethod
    def parse(cls, string):
        # Want to slurp characters until a comma is encountered (new arg)
        # or an unmatched closing paren encountered (end of list)
        i = 0
        paren_cnt = 0
        while True:
            if string[i] == "(":
                paren_cnt += 1
            elif string[i] == ")":
                paren_cnt -= 1

            if paren_cnt < 0 or string[i] == ",":
                break
            i += 1

        # Handle comma and paren cases
        arg_str = string[:i]
        if string[i] == ")":
            rest = string[i:]
        else:
            rest = string[i+1:]

        # Handle during(e) cases, constants, and variables,
        if "(" in arg_str:
            event_type, arg = arg_str.replace(")", "").split("(")
            arg = Variable(arg, arg_type="Event", event_type=event_type)
        elif arg_str.isupper():
            arg = Constant(arg_str)
        else:
            arg = Variable(arg_str)

        return arg, rest

def demo():
    semstr = "chased(during(e),x,y), Agent(e,x), Theme(e,y), ISA(x,CAT)"
    sem = SemanticParser.parse(semstr)

if __name__ == '__main__':
    demo()