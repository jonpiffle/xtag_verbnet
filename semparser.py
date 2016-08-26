from semantics import Semantics, Relation, Variable, Constant, Token, AndVariable, OrVariable

class SemanticParser(object):
    @classmethod
    def parse(cls, string):
        """Returns a Semantic object"""
        string = string.replace(" ", "")
        if "|" in string:
            quant_str, string = string.split("|")
        else:
            quant_str, string = "", string

        # Parse conjuncted relations
        relations = []
        while len(string) > 0:
            relation, string = RelationParser.parse(string)
            relations.append(relation)
        sem = Semantics(relations)

        # Parse any quantifiers
        quantification_dict = QuantificationParser.parse(quant_str)
        sem.quantification_dict = quantification_dict

        return sem

class QuantificationParser(object):
    @classmethod
    def parse(cls, string):
        quantification_dict = {}
        quants = string.split(",")
        for quant_str in quants:

            if quant_str == "":
                continue

            quant_str = quant_str.replace(")", "")
            quant_str, var_str = quant_str.split("(")
            if quant_str == "EXISTS":
                quant = Token.EXISTS
            elif quant_str == "FORALL":
                quant = Token.FORALL
            else:
                assert False

            quantification_dict[Variable(var_str)] = quant
        return quantification_dict

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
        while i < len(string):
            if string[i] == "(":
                paren_cnt += 1
            elif string[i] == ")":
                paren_cnt -= 1

            if paren_cnt < 0 or string[i] == ",":
                break
            i += 1

        # Handle end of string, paren, comma cases
        if i == len(string):
            arg_str = string
            rest = ""
        elif string[i] == ")":
            arg_str = string[:i]
            rest = string[i:]
        else:
            arg_str = string[:i]
            rest = string[i+1:]

        # Handle during(e) cases, constants, and variables,
        if "(" in arg_str:
            text, arg = arg_str.replace(")", "").split("(")
            if text == "AND":
                arg2, rest = VariableParser.parse(rest)
                arg = AndVariable(Variable(arg), arg2)
                rest = rest[1:] # remove closing paren
            elif text == "OR":
                arg2, rest = VariableParser.parse(rest)
                arg = OrVariable(Variable(arg), arg2)
                rest = rest[1:] # remove closing paren
            else:
                arg = Variable(arg, arg_type="Event", event_type=text)
        elif arg_str.isupper() or all(not c.isalpha() for c in arg_str): #arg_str.isdigit():
            arg = Constant(arg_str)
        else:
            arg = Variable(arg_str)

        return arg, rest

def demo():
    semstr = "chased(during(e),x,y), Agent(e,x), Theme(e,y), ISA(x,CAT)"
    sem = SemanticParser.parse(semstr)
    print(sem)
    semstr = ""
    sem = SemanticParser.parse(semstr)
    print(sem)
    semstr = "EXISTS(x), EXISTS(y) | chased(during(e),x,y), Agent(e,x), Theme(e,y), ISA(x,CAT)"
    sem = SemanticParser.parse(semstr)
    print(sem)
    var_str = "x"
    var = VariableParser.parse(var_str)
    print(var)

if __name__ == '__main__':
    demo()