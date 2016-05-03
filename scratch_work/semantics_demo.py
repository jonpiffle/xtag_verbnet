import nltk
class VariableFactory(object):
    counter = 0

    @classmethod
    def get_var(cls, pre=None):
        if pre is None:
            pre = 'z' 
        cls.counter += 1
        return Variable('%s%d' % (pre, cls.counter))

class Semantics(object):
    def __init__(self, relations):
        for r in relations:
            assert isinstance(r, Relation)
        self.relations = relations

    def __str__(self):
        return " ^ ".join([str(r) for r in self.relations])

    def __repr__(self):
        return str(self)

    def apply_binding(self, rename_dict):
        for r in self.relations:
            r.apply_binding(rename_dict)

class Constant(object):
    def __init__(self, name):
        self.name = name

    def apply_binding(self, rename_dict):
        pass

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

class Variable(object):
    def __init__(self, name):
        self.name = name

    def apply_binding(self, rename_dict):
        if self.name in rename_dict:
            self.name = rename_dict[self.name]

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    def __eq__(self, o):
        return isinstance(o, Variable) and o.name == self.name

class Relation(object):
    def __init__(self, name, args):
        for a in args:
            assert isinstance(a, Variable) or isinstance(a, Constant) or isinstance(a, Relation) or isinstance(a, Semantics)
        self.name = name
        self.args = args

    def apply_binding(self, rename_dict):
        for a in self.args:
            a.apply_binding(rename_dict)

    def __str__(self):
        return "%s(%s)" % (self.name, ",".join([str(a) for a in self.args]))

    def __repr__(self):
        return str(self)

class PartialSentence(object):
    def __init__(self, tree, sem):
        self.tree = tree
        self.sem = sem

    def __str__(self):
        return "%s\n%s" % (str(self.tree), str(self.sem))

    def __repr__(self):
        return str(self)

def find(t, label):
    for s in t.subtrees():
        if s.label() == label:
            return s

def prefix(t):
    return t.label().split("_")[0]

def concat(s1, s2):
    return Semantics(s1.relations + s2.relations)

def substitute(ps1, ps2, label):
    node = find(ps1.tree, label)
    assert node is not None
    assert prefix(node) == ps2.tree.label()
    rename_dict = {node.open_var.name: ps2.tree.sub_var.name}
    ps1.sem.apply_binding(rename_dict)
    ps1.sem = concat(ps1.sem, ps2.sem)

    for c in ps2.tree:
        node.append(c)
    node.entity = ps2.tree.entity

    return ps1

def find_foot(t):
    foot_label = prefix(t) + "_f"
    return find(t, foot_label)

def adjoin(ps1, ps2, label):
    node = find(ps1.tree, label)
    assert node is not None
    assert prefix(node) == prefix(ps2.tree)
    foot = find_foot(ps2.tree)
    assert foot is not None

    # Semantics
    for s in ps2.tree.subtrees():
        s.entity = node.entity
    rename_dict = {ps2.tree.var.name: node.entity.name}
    ps2.sem.apply_binding(rename_dict)
    ps1.sem = concat(ps1.sem, ps2.sem)

    # Syntax
    # Move children of adjunction node to foot node
    for c in node:
        foot.append(c) 

    # Replace original children with new node + foot node
    for _ in node:
        node.pop()
    for c in ps2.tree:
        node.append(c)

    return ps1

def demo():
    e = Variable('e')
    x = Variable('x')
    y = Variable('y')
    r0 = Relation('During', [e])
    r1 = Relation('Motion', [r0, x])
    r2 = Relation('During', [e])
    r3 = Relation('Motion', [r2, y])
    r4 = Relation('Agent', [e, x])
    r5 = Relation('Theme', [e, y])
    s = Semantics([r1, r3, r4, r5])
    chase_tree = nltk.Tree.fromstring("(S_r (NP_0 ) (VP (V (chase )) (NP_1)))")
    find(chase_tree, "NP_0").open_var = x
    find(chase_tree, "NP_1").open_var = y
    chase_ps = PartialSentence(chase_tree, s)
    for s in chase_tree.subtrees():
        s.entity = e
    print(chase_ps)
    print()

    d = VariableFactory.get_var()
    dog = Constant('Dog')
    r = Relation("ISA", [d, dog])
    s = Semantics([r])
    dog_tree = nltk.Tree.fromstring("(NP (NN (dog )))")
    dog_tree.sub_var = d
    dog_ps = PartialSentence(dog_tree, s)
    for s in dog_tree.subtrees():
        s.entity = d
    print(dog_ps)
    print()

    c = VariableFactory.get_var()
    cat = Constant('Cat')
    r = Relation("ISA", [c, cat])
    s = Semantics([r])
    cat_tree = nltk.Tree.fromstring("(NP (NN (cat )))")
    cat_tree.sub_var = c
    cat_ps = PartialSentence(cat_tree, s)
    for s in cat_tree.subtrees():
        s.entity = c
    print(cat_ps)
    print()

    ps = substitute(chase_ps, dog_ps, "NP_0")
    ps = substitute(ps, cat_ps, "NP_1")
    print(ps)
    print()

    v = VariableFactory.get_var()
    red = Constant("Red")
    r = Relation("ISA", [v, red])
    s = Semantics([r])
    red_tree = nltk.Tree.fromstring("(NP_r (A (red )) (NP_f ))") 
    red_tree.var = v
    red_ps = PartialSentence(red_tree, s)
    for s in red_tree.subtrees():
        s.entity = v
    print(red_ps)
    print()

    ps = adjoin(ps, red_ps, "NP_0")
    print(ps)
    print()

if __name__ == '__main__':
    demo()