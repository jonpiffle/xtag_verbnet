import nltk, re, itertools, copy

from collections import defaultdict

class VariableBinding(object):
    def __init__(self, binding=None):
        if binding is None:
            binding = {}

        self.binding = {}
        for k,v in binding.items():
            self[k] = v

    def items(self):
        return self.binding.items()

    def __setitem__(self, key, value):
        self.binding[key.copy()] = value.copy()

    def __contains__(self, key):
        return key in self.binding

    def __getitem__(self, key):
        return self.binding[key].copy()

    def __str__(self):
        return str(self.binding)

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

    @classmethod
    def reset(cls):
        cls.count_dict = defaultdict(int)

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
        self.quantification_dict[v] = quant

    def event(self):
        """Returns any 'event' variables in the semantics"""
        events = [v for v in self.variables() if v.arg_type == "Event"]
        return events[0]

    def variables(self):
        """Returns all variables in all subexpressions"""
        return set([v for r in self.relations for v in r.variables()])

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
        self.relations = [r.apply_binding(rename_dict) for r in self.relations]
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

    def get_rename_dict(self, suffixes_used, sem_var=None):
        """
        Returns a rename dictionary specifying what each variable with a conflict
        should be renamed to in order to avoid conflicts with the suffixes used
        """
        rename_dict = VariableBinding()
        variables = self.variables()
        if sem_var is not None and isinstance(sem_var, CompoundVariable):
            variables.add(sem_var.first)
            variables.add(sem_var.second)
        elif sem_var is not None:
            variables.add(sem_var)

        for v in variables:
            if v.suffix() in suffixes_used[v.prefix()]:
                new_suffix = max(suffixes_used[v.prefix()]) + 1
                new_var_name = v.prefix() + str(new_suffix)
                suffixes_used[v.prefix()].add(new_suffix)
                rename_dict[v] = Variable(new_var_name)
        return rename_dict

    def __eq__(self, other):
        return set([str(r) for r in self.relations]) == set([str(r) for r in other.relations])

    def equiv(self, other):
        ents1 = set(v.name for v in self.variables())
        ents2 = set(v.name for v in other.variables())

        if len(ents1) != len(ents2):
            return False
        if len(ents1) == 0:
            return True

        for entity_perm in itertools.permutations(ents1):
            binding = zip(entity_perm, ents2)
            binding = {Variable(e1): Variable(e2) for e1, e2 in binding}
            binding = VariableBinding(binding)
            bound = copy.deepcopy(self).apply_binding(binding)
            if bound == other:
                return True
        return False

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
        rename_dict = VariableBinding()
        for rel in rels:
            event = rel.event() 

            # Event starts out as capital (E, E1, etc) so want to map it to
            # lowercase (e1, e2, etc)
            if event not in rename_dict:
                new_event = VariableFactory.get_var(pre='e')
                rename_dict[event] = new_event

            for v in rel.variables():
                if v in rename_dict or v.arg_type == "Constant":
                    continue

                # Map "Agent" to "a1", etc.
                new_var = VariableFactory.get_var(pre=v.name[0])
                rename_dict[v] = new_var

                # These are the variables that need to be broken out into
                # relations. ie Agent -> Agent(e1, a1)
                # This then gets assigned to a1, as it will be given to the
                # subst node assigned to a1
                if v.arg_type == "ThemRole":
                    new_rel = Relation(v.name, [Variable(event.name, arg_type="Event"), new_var])
                    new_v = rename_dict[v]
                    sem_dict[new_v.name].append(new_rel)

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
        assert isinstance(name, str)
        self.name = name

    def apply_binding(self, rename_dict):
        """
        Returns self after renaming, if necessary. Typically you would not 
        expect constants to get renamed, but this has useful practical applications,
        such as allowing for specific anchors to make contributions to a more
        general frame, via a placeholder
        """
        assert isinstance(rename_dict, VariableBinding)
        if self in rename_dict:
            return rename_dict[self]
        return self

    def copy(self):
        return Constant(self.name)

    def __eq__(self, o):
        return isinstance(o, Variable) and o.name == self.name

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self)

class Variable(object):
    """Class representing an FOL variable"""
    def __init__(self, name, arg_type=None, event_type=None):
        assert isinstance(name, str)
        self.name = name
        self.orig_name = name
        self.arg_type = arg_type # This is useful when parsing from verbnet
        self.event_type = event_type # Only used for event vars: during, end, start, result
        self.missing = False

    def apply_binding(self, rename_dict):
        """Returns self after renaming, if necessary"""
        assert isinstance(rename_dict, VariableBinding)
        if self in rename_dict:
            return rename_dict[self]
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

    def copy(self):
        new_var = Variable(self.name, self.arg_type, self.event_type)
        new_var.orig_name = self.orig_name
        new_var.missing = self.missing
        return new_var

    def __str__(self):
        #if self.event_type is not None:
        #    return "%s(%s)" % (str(self.event_type), str(self.name))
        return str(self.name)

    def __repr__(self):
        return str(self)

    def __eq__(self, o):
        return isinstance(o, Variable) and o.name == self.name

    def __hash__(self):
        return hash(self.name)

class CompoundVariable(Variable):
    def __init__(self, first, second):
        self.first = first
        self.second = second

    def apply_binding(self, rename_dict):
        self.first = self.first.apply_binding(rename_dict)
        self.second = self.second.apply_binding(rename_dict)
        return self

class AndVariable(CompoundVariable):
    def copy(self):
        return AndVariable(self.first, self.second)

    def __str__(self):
        return "AND(%s,%s)" % (str(self.first), str(self.second))

class OrVariable(CompoundVariable):
    def copy(self):
        return OrVariable(self.first, self.second)

    def __str__(self):
        return "OR(%s,%s)" % (str(self.first), str(self.second))

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
        return set([v for v in self.args if isinstance(v, Variable) and not isinstance(v, CompoundVariable)])

    def apply_binding(self, rename_dict):
        """Returns self after renaming all variables (if necessary)"""
        self.args = [a.apply_binding(rename_dict) for a in self.args]
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
