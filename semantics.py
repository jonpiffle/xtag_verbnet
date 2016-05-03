import nltk, re

from collections import defaultdict

class VariableFactory(object):
    """
    Class for generating unique variables
    """
    count_dict = defaultdict(int)

    @classmethod
    def get_var(cls, pre=None):
        """Returns next available variable name given a prefix (or default, z)"""
        if pre is None:
            pre = 'z' 
        pre = pre.lower()
        cls.count_dict[pre] += 1
        return Variable('%s%d' % (pre, cls.count_dict[pre]))

class Token(object):
    EXISTS = u"\u2203"
    FORALL = u"\u2200"

class Semantics(object):
    """
    Class representing a conjunction of relations, used for specifying the
    semantics of a sentence.
    """

    def __init__(self, relations):
        for r in relations:
            assert isinstance(r, Relation)
        self.relations = relations
        self.quantification_dict = {}

    def set_quantification(self, v, quant):
        self.quantification_dict[v.name] = quant

    def event(self):
        """Returns any 'event' variables in the semantics"""
        events = [v for v in self.variables() if v.arg_type == "Event"]
        return events[0]

    def variables(self):
        """Returns all variables in all subexpressions"""
        return [v for r in self.relations for v in r.variables()]

    def concat(self, other):
        """Returns new semantics formed by concatenating other to self"""
        new_sem = Semantics(self.relations + other.relations)
        new_sem.quantification_dict.update(other.quantification_dict)
        return new_sem

    def __str__(self):
        quant_str = ",".join("%s%s" % (v, k) for k,v in self.quantification_dict.items())
        if len(quant_str) > 0:
            quant_str = quant_str + " "
        return quant_str + " ^ ".join([str(r) for r in self.relations])

    def __repr__(self):
        return str(self)

    def apply_binding(self, rename_dict):
        """
        Returns self after applying the binding given by the rename dict to
        all subexpressions
        """
        # Need to update quantification dictionary
        new_quant_dict = {}
        for v, quant in self.quantification_dict.items():
            if v in rename_dict:
                new_quant_dict[rename_dict[v]] = quant
            else:
                new_quant_dict[v] = quant
        self.quantification_dict = new_quant_dict

        # And need to update all relations
        for r in self.relations:
            r.apply_binding(rename_dict)
        return self

    def suffixes_used(self):
        """
        Returns a dictionary mapping a variable prefix to all suffixes that 
        are currently in use for that prefix. i.e. {e: [1,2], z: [1,2,3,4,5]}
        """
        suffixes = defaultdict(set)
        for v in self.variables():
            suffixes[v.prefix()].add(v.suffix())
        return suffixes

    def get_rename_dict(self, suffixes_used):
        """
        Returns a rename dictionary specifying what each variable with a conflict
        should be renamed to in order to avoid conflicts with the suffixes used
        """
        rename_dict = {}
        for v in self.variables():
            if v.suffix() in suffixes_used[v.prefix()]:
                new_suffix = max(suffixes_used[v.prefix()]) + 1
                new_var_name = v.prefix() + str(new_suffix)
                suffixes_used[v.prefix()].add(new_suffix)
                rename_dict[v.name] = new_var_name
        return rename_dict

    @classmethod
    def semdict_fromxml(cls, xml):
        """
        Returns a dictionary mapping variable names to Semantics object given 
        the PRED XML tree provided in the verbnet frames. The special "Event" 
        variable has the key "Event" instead of its actual name ("e1", etc).
        This dictionary is used to map tree components to their individual 
        semantic components. For verb trees, the root gets all relations 
        except the "ThemRoles", which go to the noun subs
        """
        # First parse each pred to a relation of variables
        rels = []
        for rel_xml in xml.findall("PRED"):
            rel_name = rel_xml.attrib["value"]
            args = []
            for arg_xml in rel_xml.find("ARGS").findall("ARG"):
                arg_type = arg_xml.attrib["type"]
                arg_str = arg_xml.attrib["value"]

                # This happens in the case of event type modifiers
                # ie "during(E)", "start(E)", etc.
                if "(" in arg_str:
                    event_type, arg = arg_str.replace(")", "").split("(")
                    arg = Variable(arg, arg_type=arg_type, event_type=event_type)
                elif arg_type == "Constant":
                    arg = Constant(arg_str)
                else:
                    arg = Variable(arg_str, arg_type=arg_type)

                # "?" means that the arg is in class but not the specific frame
                if "?" in arg_str:
                    arg.missing = True
                    arg.name = arg.name[1:]

                args.append(arg)
            rel = Relation(rel_name, args)
            rels.append(rel)

        # Clean up the semantics and separate by dominating variable
        sem_dict = defaultdict(list)
        rename_dict = {}
        for rel in rels:
            event = rel.event() 

            # Event starts out as capital (E, E1, etc) so want to map it to
            # lowercase (e1, e2, etc)
            if event.name not in rename_dict:
                new_event = VariableFactory.get_var(pre='e')
                rename_dict[event.name] = new_event.name

            for v in rel.variables():
                if v.name in rename_dict or v.arg_type == "Constant":
                    continue

                # Map "Agent" to "a1", etc.
                new_var = VariableFactory.get_var(pre=v.name[0])
                rename_dict[v.name] = new_var.name

                # These are the variables that need to be broken out into
                # relations. ie Agent -> Agent(e1, a1)
                # This then gets assigned to a1, as it will be given to the
                # subst node assigned to a1
                if v.arg_type == "ThemRole":
                    new_rel = Relation(v.name, [Variable(event.name, arg_type="Event"), new_var])
                    new_v = rename_dict[v.name]
                    sem_dict[new_v].append(new_rel)

                # This is for information conveyed by the specific lexicalization
                # of a verb class. A dummy placeholder is used until the anchor 
                # is given later. The relation is still associated with the root
                elif v.arg_type == "VerbSpecific":
                    new_rel = Relation(v.name, [Variable(event.name, arg_type="Event"), new_var, Constant("__ANCHOR__")])
                    sem_dict["Event"].append(new_rel)

            # All of the initial relations get assigned to the main event 
            # (which will be assigned to the root of the tree
            sem_dict["Event"].append(rel)

        # Convert every list of relations to a Semantics object and apply the necessary renames 
        sem_dict = {e: Semantics(r).apply_binding(rename_dict) for e,r in sem_dict.items()}
        return sem_dict

class Constant(object):
    """Class representing an FOL symbol/constant"""

    def __init__(self, name):
        self.name = name

    def apply_binding(self, rename_dict):
        """
        Returns self after renaming, if necessary. Typically you would not 
        expect constants to get renamed, but this has useful practical applications,
        such as allowing for specific anchors to make contributions to a more
        general frame, via a placeholder
        """

        if self.name in rename_dict:
            self.name = rename_dict[self.name]
        return self

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

class Variable(object):
    """Class representing an FOL variable"""
    def __init__(self, name, arg_type=None, event_type=None):
        self.name = name
        self.orig_name = name
        self.arg_type = arg_type # This is useful when parsing from verbnet
        self.event_type = event_type # Only used for event vars: during, end, start, result
        self.missing = False

    def apply_binding(self, rename_dict):
        """Returns self after renaming, if necessary"""
        if self.name in rename_dict:
            self.name = rename_dict[self.name]
        return self

    def prefix(self):
        """Returns variable prefix (lowercase letters to start name)"""
        return re.match('([a-z]+)', self.name).group(1)

    def suffix(self):
        """Returns variable suffix (first set of digits cast to int, or 0)"""
        match = re.search('(\d+)', self.name)
        if match is None:
            return 0
        else:
            return int(match.group(1))

    def __str__(self):
        if self.event_type is not None:
            return "%s(%s)" % (self.event_type, self.name)
        return self.name

    def __repr__(self):
        return str(self)

    def __eq__(self, o):
        return isinstance(o, Variable) and o.name == self.name

    def __hash__(self):
        return hash(str(self))

class AndVariable(Variable):
    def __init__(self, name, first, second):
        self.name = name
        self.first = first
        self.second = second

    def __str__(self):
        return "AND(%s,%S)" % (str(self.first), str(self.second))

class OrVariable(Variable):
    def __init__(self, name, first, second):
        self.name = name
        self.first = first
        self.second = second

    def __str__(self):
        return "OR(%s,%S)" % (str(self.first), str(self.second))

class Relation(object):
    """
    Class representing an FOL relation. A relation has a name and takes args
    which are variables or constants. 
    """
    def __init__(self, name, args):
        for a in args:
            assert isinstance(a, Variable) or isinstance(a, Constant)
        self.name = name
        self.args = args

    def variables(self):
        """Returns list of all variables in relation (may be deeply nested)"""
        return [v for v in self.args if isinstance(v, Variable)]

    def apply_binding(self, rename_dict):
        """Returns self after renaming all variables (if necessary)"""
        for a in self.args:
            a.apply_binding(rename_dict)
        return self

    def event(self):
        """Returns the first event variable, if exists"""
        for v in self.variables():
            if v.arg_type == "Event":
                return v

    def __str__(self):
        return "%s(%s)" % (self.name, ",".join([str(a) for a in self.args]))

    def __repr__(self):
        return str(self)
