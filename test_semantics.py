import inflection

from collections import defaultdict

from grammar import Grammar
from verbnet import VerbNet, XTAGMapper
from propbank import Propbank
from derivation import DerivationTree
from semantics import Semantics, VariableFactory, Constant, Relation, Token, AndVariable, Variable
from tagtree import SemTree
from semparser import SemanticParser
from semgrammar import SemTreeGrammar

g = Grammar.load()
vnet = VerbNet.load()
mapper = XTAGMapper.load()
propbank = None #Propbank.load()
s = SemTreeGrammar(g, vnet, mapper, propbank)

def test_alphanx0Vnx1():
    chase = s.get_semtree('alphanx0Vnx1', 'chase', lemma='chase')
    cat = s.get_semtree('alphaNXN', 'cat')
    dog = s.get_semtree('alphaNXN', 'dog')
    chase = chase.substitute(cat, 'NP_0')
    chase = chase.substitute(dog, 'NP_1')
    sem = SemanticParser.parse("motion(during(e1),x0), motion(during(e1),x1), Agent(e1,x0), ISA(x0,CAT), Theme(e1,x1), ISA(x1,DOG)")
    assert chase.full_semantics().equiv(sem)

def test_betaAn():
    red = s.get_semtree('betaAn', 'red')
    cat = s.get_semtree('alphaNXN', 'cat')
    dog = s.get_semtree('alphaNXN', 'dog')
    chase = s.get_semtree('alphanx0Vnx1', 'chase', lemma='chase')
    chase = chase.substitute(cat, 'NP_0')
    chase = chase.substitute(dog, 'NP_1')
    chase = chase.adjoin(red, "N")
    sem = SemanticParser.parse("motion(during(e1),x0), motion(during(e1),x1), Agent(e1,x0), ISA(x0,CAT), ISA(x0,RED), Theme(e1,x1), ISA(x1,DOG)")
    assert chase.full_semantics().equiv(sem)

def test_betaVvx():
    will = s.get_semtree('betaVvx', 'will')
    chase = s.get_semtree('alphanx0Vnx1', 'chase', lemma='chase')
    cat = s.get_semtree('alphaNXN', 'cat')
    dog = s.get_semtree('alphaNXN', 'dog')
    chase = chase.substitute(cat, 'NP_0')
    chase = chase.substitute(dog, 'NP_1')
    chase = chase.adjoin(will, "VP")
    sem = SemanticParser.parse("motion(during(e1),x0), motion(during(e1),x1), Agent(e1,x0), ISA(x0,CAT), Theme(e1,x1), ISA(x1,DOG)")
    assert chase.full_semantics().equiv(sem)

def test_betanxPnx():
    behind = s.get_semtree('betanxPnx', 'behind')
    run = s.get_semtree('alphanx0V', 'run', lemma='run')
    dog = s.get_semtree('alphaNXN', 'dog')
    cat = s.get_semtree('alphaNXN', 'cat')
    run = run.substitute(dog, 'NP_0')
    run = run.adjoin(behind, 'NP_0')
    run = run.substitute(cat, 'NP')
    sem = SemanticParser.parse("motion(during(e1),x5), Theme(e1,x5), ISA(x5,DOG), behind(x5,x4), ISA(x4,CAT)")
    assert run.full_semantics().equiv(sem)

def test_betavxPnx():
    behind = s.get_semtree('betavxPnx', 'behind')
    run = s.get_semtree('alphanx0V', 'run', lemma='run')
    dog = s.get_semtree('alphaNXN', 'dog')
    cat = s.get_semtree('alphaNXN', 'cat')
    run = run.substitute(dog, 'NP_0')
    run = run.adjoin(behind, 'VP')
    run = run.substitute(cat, 'NP')
    sem = SemanticParser.parse("motion(during(e1),x0), Theme(e1,x0), ISA(x0,DOG), behind(e1,x1), ISA(x1,CAT)")
    assert run.full_semantics().equiv(sem)

def test_betasPUs():
    semi = s.get_semtree('betasPUs', ';')
    run = s.get_semtree('alphanx0V', 'run', lemma='run')
    dog = s.get_semtree('alphaNXN', 'dog')
    run2 = s.get_semtree('alphanx0V', 'run', lemma='run')
    cat = s.get_semtree('alphaNXN', 'cat')
    run = run.substitute(dog, "NP_0")
    run2 = run2.substitute(cat, "NP_0")
    run = run.adjoin(semi, 'S_r')
    run = run.substitute(run2, 'S_1')
    assert str(run.sem_var) == "AND(e1,e2)"
    sem = SemanticParser.parse("motion(during(e1),x), Theme(e1,x), ISA(x,DOG), motion(during(e2),x1), Theme(e2,x1), ISA(x1,CAT)")
    assert run.full_semantics().equiv(sem)

def test_betaARBvx():
    run = s.get_semtree('alphanx0V', 'run', lemma='run')
    dog = s.get_semtree('alphaNXN', 'dog')
    obv = s.get_semtree('betaARBvx', 'obviously')
    run = run.substitute(dog, "NP_0")
    run = run.adjoin(obv, "VP")
    sem = SemanticParser.parse("motion(during(e1),x), Theme(e1,x), ISA(x,DOG), obviously(e1)")
    assert run.full_semantics().equiv(sem)

def test_betanxPUnx():
    run = s.get_semtree('alphanx0V', 'run', lemma='run')
    dog = s.get_semtree('alphaNXN', 'dog')
    cat = s.get_semtree('alphaNXN', 'cat')
    comma = s.get_semtree('betanxPUnx', ',')
    run = run.substitute(dog, "NP_0")
    run = run.adjoin(comma, "NP_0")
    run = run.substitute(cat, "NP")
    sem = SemanticParser.parse("motion(during(e1),x), equal(x,x1), Theme(e1,x), ISA(x,DOG), ISA(x1,CAT)")
    assert run.full_semantics().equiv(sem)

def test_betaPUs():
    run = s.get_semtree('alphanx0V', 'run', lemma='run')
    dog = s.get_semtree('alphaNXN', 'dog')
    comma = s.get_semtree('betaPUs', ',')
    run = run.substitute(dog, "NP_0")
    run = run.adjoin(comma, "S_r")
    sem = SemanticParser.parse("motion(during(e1),x), Theme(e1,x), ISA(x,DOG)")
    assert run.full_semantics().equiv(sem)

def test_betaVs():
    run = s.get_semtree('alphanx0V', 'run', lemma='run')
    dog = s.get_semtree('alphaNXN', 'dog')
    does = s.get_semtree('betaPUs', 'does')
    run = run.substitute(dog, "NP_0")
    run = run.adjoin(does, "S_r")
    sem = SemanticParser.parse("motion(during(e1),x), Theme(e1,x), ISA(x,DOG)")
    assert run.full_semantics().equiv(sem)

def test_betanx1CONJnx2():
    run = s.get_semtree('alphanx0V', 'run', lemma='run')
    dog = s.get_semtree('alphaNXN', 'dog')
    cat = s.get_semtree('alphaNXN', 'cat')
    conj = s.get_semtree('betanx1CONJnx2', 'and')
    run = run.substitute(dog, 'NP_0')
    run = run.adjoin(conj, "NP_0")
    run = run.substitute(cat, "NP_2")
    sem = SemanticParser.parse("motion(e1,AND(x1,x2)), Theme(e1,AND(x1,x2)), ISA(x1,DOG), ISA(x2,CAT)")
    assert run.full_semantics().equiv(sem)

def test_betanxGnx():
    dog = s.get_semtree('alphaNXN', 'dog')
    john = s.get_semtree('alphaNXN', 'John')
    poss = s.get_semtree('betanxGnx', '\'s')
    dog = dog.adjoin(poss, "NP")
    dog = dog.substitute(john, "NP-1")
    sem = SemanticParser.parse("belongs_to(x1,x2), ISA(x2,JOHN), ISA(x1,DOG)")
    assert dog.full_semantics().equiv(sem)

def test_betavxPs():
    because = s.get_semtree('betavxPs', 'because')
    run = s.get_semtree('alphanx0V', 'run', lemma='run')
    dog = s.get_semtree('alphaNXN', 'dog')
    run2 = s.get_semtree('alphanx0V', 'run', lemma='run')
    cat = s.get_semtree('alphaNXN', 'cat')
    run = run.substitute(dog, "NP_0")
    run2 = run2.substitute(cat, "NP_0")
    run = run.adjoin(because, "VP")
    run = run.substitute(run2, "S")
    sem = SemanticParser.parse("motion(e1,x1), Theme(e1,x1), ISA(x1,DOG), because(e1,e2), motion(e2,x2), Theme(e2,x2), ISA(x2,CAT)")
    assert run.full_semantics().equiv(sem)

def test_betas1CONJs2():
    conj = s.get_semtree('betas1CONJs2', 'and')
    run = s.get_semtree('alphanx0V', 'run', lemma='run')
    dog = s.get_semtree('alphaNXN', 'dog')
    run2 = s.get_semtree('alphanx0V', 'run', lemma='run')
    cat = s.get_semtree('alphaNXN', 'cat')
    run = run.substitute(dog, "NP_0")
    run2 = run2.substitute(cat, "NP_0")
    run = run.adjoin(conj, 'S_r')
    run = run.substitute(run2, 'S_2')
    assert str(run.sem_var) == "AND(e1,e2)"
    sem = SemanticParser.parse("motion(during(e1),x), Theme(e1,x), ISA(x,DOG), motion(during(e2),x1), Theme(e2,x1), ISA(x1,CAT)")
    assert run.full_semantics().equiv(sem)

def test_betaARBs():
    run = s.get_semtree('alphanx0V', 'run', lemma='run')
    dog = s.get_semtree('alphaNXN', 'dog')
    obv = s.get_semtree('betaARBs', 'obviously')
    run = run.substitute(dog, "NP_0")
    run = run.adjoin(obv, "S_r")
    sem = SemanticParser.parse("motion(during(e1),x), Theme(e1,x), ISA(x,DOG), obviously(e1)")
    assert run.full_semantics().equiv(sem)

def test_betaCONJs():
    conj = s.get_semtree('betaCONJs', 'and')
    chase = s.get_semtree('alphanx0Vnx1', 'chase', lemma='chase')
    cat = s.get_semtree('alphaNXN', 'cat')
    dog = s.get_semtree('alphaNXN', 'dog')
    chase = conj.substitute(chase, 'S_r')
    chase = chase.substitute(cat, 'NP_0')
    chase = chase.substitute(dog, 'NP_1')
    sem = SemanticParser.parse("motion(during(e1),x0), motion(during(e1),x1), Agent(e1,x0), ISA(x0,CAT), Theme(e1,x1), ISA(x1,DOG)")
    assert chase.full_semantics().equiv(sem)

if __name__ == '__main__':
    funcs = [
        test_alphanx0Vnx1,
        test_betaAn,
        test_betaVvx,
        test_betanxPnx,
        test_betavxPnx,
        test_betasPUs,
        test_betaARBvx,
        test_betanxPUnx,
        test_betaPUs,
        test_betaVs,
        test_betanx1CONJnx2,
        test_betanxGnx,
        test_betavxPs,
        test_betas1CONJs2,
        test_betaARBs,
        test_betaCONJs,
    ]
    for func in funcs:
        func()

    print(g.get("alphaN1s0").tree_family)
    print(g.get("betanx0Vs1").tree_family)
    print(g.get("alphas0N1").tree_family)

    tree_set = [
        #"alphaNXN", # 78483 
        #"betaDnx", # 31668 
        #"betaNn", # 21141 
        #"betaVvx", # 15070 
        #"betaAn", # 13792 
        #"betanxPnx", # 8997 
        #"betavxPnx", # 8917 
        #"betasPUs", # 5689 
        #"alphanx0Vnx1", # 4493 
        #"alphanx1V", # 4420 
        #"alphanx1V-PRO", # 4170 
        "alphaN1s0", # 3662 
        "betanx0Vs1", # 3615 
        "alphas0N1", # 3495 
        #"betaARBvx", # 3256 
        #"betanxPUnx", # 3140 
        #"alphanx0Vnx1-PRO", # 3082 
        #"betaVs", # 2668 
        #"betaPUs", # 2628 
        #"betanx1CONJnx2", # 2568 
        #"betanxGnx", # 2489 
        #"betavxPs", # 2299 
        #"betas1CONJs2", # 2169 
        #"betaARBs", # 2015 
        #"betaCONJs", # 1966 
        "alphanx0Pnx1", # 1875 
        "betanxPUs", # 1821 
        "alphanx0BEnx1", # 1813 
        "betaCOMPs", # 1786 
        "alphanx0N1-PRO", # 1734 
        "betaPnxs", # 1627 
        "betavxARB", # 1558 
        "alphanx0Pnx1-PRO", # 1483 
        "alphanx0N1", # 1380 
        "betasPU", # 1371 
        "betanx0Vs1-PRO", # 1318 
        "betaPss", # 1228 
        "betaN1nx1V", # 1217 
        "alphanx0Ax1", # 1171 
        "alphanx0Ax1-PRO", # 1166 
        "alphas0Ax1", # 1041 
        "alphanx0V", # 987 
        "alphaD", # 941 
        "alphaXGnx0Vs1", # 937 
        "alphaPu", # 889 
        "alphanx0V-PRO", # 848 
        "betaN0nx0Vnx1", # 720 
        "alphaPXPnx", # 687 
        "betaARBa", # 687 
        "betan1CONJn2", # 678 
        "alphaN", # 678 
        "alphaDnx0V", # 630 
        "alphanx2Vnx1", # 609 
        "betasPUnx", # 607 
        "betaXnx0Vs1", # 568 
        "betavxN", # 528 
        "betaN0nx0N1", # 502 
        "alphaNXNs", # 498 
        "betaNPnx1nx0Pnx1", # 496 
        "betaN0nx0Pnx1", # 482 
        "betaNEGvx", # 461 
        "alphanx2Vnx1-PRO", # 405 
        "alphaNXnxG", # 402 
        "alphaXW0nx0Vs1", # 384 
        "alphaDnx0Vs1", # 340 
        "betaVergativen", # 325 
        "alphapW1nx0Pnx1", # 313 
        "betaN1nx0Pnx1", # 301 
        "betaXNc0nx0Vs1", # 295 
        "betanxN", # 293 
        "betaN0nx0Ax1", # 290 
        "betaN0nx0V", # 286 
        "alphaP", # 260 
        "betaCnxPnx", # 239 
        "alphaW1nx1V", # 234 
        "betaARBnx", # 233 
        "betaENc1nx1V", # 232 
        "betanx1Vs2-PRO", # 205 
        "betanx1Vs2", # 203 
        "betaspuPs", # 203 
        "betaNpxs0N1", # 193 
        "betaN1nx0Vnx1", # 188 
        "betaNs", # 186 
        "betaa1CONJa2", # 180 
        "alphaA", # 176 
        "betaARBpx", # 175 
        "alphaW0nx0Vnx1", # 172 
        "betaXInx0Vs1", # 163 
        "betaARBd", # 154 
        "betaXNcnx0Vs1", # 150 
        "betaNpxnx1V", # 141 
        "alphas0Vnx1", # 136 
        "alphanx0Vplnx1", # 135 
        "betaN0nx0Vs1", # 134 
        "betanxARB", # 131 
        "alphanx0Vnx2nx1", # 130 
        "alphanx1Vpl", # 117 
        "betaNvx", # 113 
        "alphaEW1nx1V", # 112 
        "betaARBarb", # 109 
        "alphanx0Vplnx1-PRO", # 106 
        "betaspuPnx", # 105 
        "alphanx1Vpl-PRO", # 104 
        "betaCARBarb", # 101 
        "betaspuARB", # 100 
        "alphaW1nx0Vnx1", # 99 
        "betaspunxV", # 99 
        "betanx0Vnx1s2", # 94 
        "betaXnx0Vs1-PRO", # 89 
        "betanxPs", # 86 
        "betaCARBa", # 84 
        "betaspuVnx", # 80 
        "alphaAXA", # 80 
        "alphaW0nx0Vs1", # 78 
        "betaVvx-adj", # 76 
        "alphaDnxG", # 73 
        "alphaW0s0N1", # 73 
        "alphaW0nx0Pnx1", # 72 
        "alphaW0nx0V", # 70 
        "alphas0Vs1", # 68 
        "alphanx0Px1-PRO", # 67 
        "betaNpxnx0Vnx1", # 66 
        "betanx0Vnx1s2-PRO", # 64 
        "alphanx0Px1", # 64 
        "betanxVpus", # 63 
        "betavPU", # 60 
        "alphanx0VPnx1", # 56 
        "betapx1CONJpx2", # 56 
        "alphanx1Vpnx2-PRO", # 53 
        "betaaxPnx", # 52 
        "betapuARBpuvx", # 52 
        "betanxARBs", # 52 
        "alphaW1nx0Pnx1", # 52 
        "betaNpxs0Ax1", # 52 
        "alphanx0Vnx2nx1-PRO", # 51 
        "betanxP", # 51 
        "alphanx0Vnx1pnx2", # 48 
        "betavxnxARB", # 48 
        "alphanx0Vax1", # 46 
        "alphanx1Vpnx2", # 45 
        "alphaEnx1V", # 45 
        "alphaW1nx0N1", # 44 
        "betadD", # 43 
        "betaNEGa", # 42 
        "betaNpxnx0Pnx1", # 41 
        "alphaAd", # 40 
        "betaNpxnx0V", # 39 
        "alphanx0VPnx1-PRO", # 37 
        "alphaEnx1V-PRO", # 37 
        "alphaW0nx0N1", # 37 
        "betaN1nx2Vnx1", # 36 
        "betaNpxnx0Ax1", # 35 
        "betaENcnx1V", # 35 
        "alphaW0nx0Ax1", # 35 
        "betaN2nx2Vnx1", # 34 
        "alphanx0Vpl-PRO", # 31 
        "alphanx0N1s1-PRO", # 31 
        "alphaW1nx0Vs1", # 30 
        "alphanx1VPnx2", # 30 
        "alphanx0N1s1", # 29 
        "alphaAV", # 29 
        "alphaW0s0Ax1", # 27 
        "alphanx0Vpl", # 27 
        "alphanx1VP-PRO", # 26 
        "alphaW1nx2Vnx1", # 26 
        "betanxPUa", # 25 
        "betaN0nx0Px1", # 25 
        "betaNpxnx0N1", # 24 
        "alphaW2nx0Vnx2nx1", # 24 
        "betapuPpuvx", # 23 
        "betaN1nx1Vpl", # 22 
        "betavxP", # 22 
        "alphanx0Vnx1pl", # 22 
        "betaN0nx0Vplnx1", # 22 
        "betaN2nx0Vnx2nx1", # 21 
        "alphanx0Vnx1pl-PRO", # 21 
        "betaarb1CONJarb2", # 20 
        "alphanx1VPnx2-PRO", # 20 
        "alphanx1VP", # 20 
        "alphanx0Vax1-PRO", # 20 
        "alphaPW1nx0Px1", # 19 
        "alphaDEnx1V", # 18 
        "betanxnxARB", # 18 
        "betapunxVpuvx", # 18 
        "betaXN0nx0Vs1", # 18 
        "betaARBPss", # 17 
        "alphanx0lVN1", # 17 
        "alphaW2nx2Vnx1", # 16 
        "alphanx0Vnx1pnx2-PRO", # 16 
        "alphaW1nx0Vnx2nx1", # 15 
        "betaNpxnx0Vs1", # 14 
        "betaARBarbs", # 14 
        "betap1CONJp2", # 14 
        "betaN1nx1Vpnx2", # 14 
        "alphanx0Vnx1Pnx2", # 13 
        "betapunxVnx1pus", # 12 
        "betad1CONJd2", # 12 
        "alphapW1ItVpnx1s2", # 12 
        "betaax1CONJax2", # 11 
        "betavxARBPnx", # 11 
        "betaN1nx1Vs2", # 11 
        "betasnxARB", # 10 
        "alphanx0Vpnx1", # 10 
        "betaEN1nx1V", # 10 
        "betaspunxVnx1", # 10 
        "alphanx0Vpnx1-PRO", # 9 
        "betanARB", # 9 
        "betaN0nx0Vnx2nx1", # 9 
        "betaN0nx0Vpl", # 9 
        "betaaARB", # 9 
        "alphaW0nx0Vplnx1", # 8 
        "betaN0nx0Vax1", # 8 
        "alphaDnx0VPnx1", # 7 
        "alphanx0Vnx1Pnx2-PRO", # 7 
        "betaN1nx0Vnx2nx1", # 7 
        "betaARBPnxs", # 7 
        "alphapW2nx0Vnx1pnx2", # 7 
        "alphaW1ItVnx1s2", # 7 
        "alphanx1Vp-PRO", # 7 
        "alphaAXAs", # 6 
        "alphaW0nx0Px1", # 6 
        "alphaDnx0Vpl", # 6 
        "betaN1nx0Vplnx1", # 6 
        "betavpunxVpu", # 6 
        "alphaPXP", # 5 
        "betaN0nx0VPnx1", # 5 
        "betavpuVnxpu", # 5 
        "alphanx1Vp", # 5 
        "betaN0nx0Vnx1s2", # 5 
        "alphaW0nx0Vnx2nx1", # 5 
        "betaDAax", # 4 
        "alphaW1nx0Vnx1s2", # 4 
        "betaXNpxnx0Vs1", # 4 
        "alphaW1nx1Vs2", # 4 
        "alphaW1nx0Vplnx1", # 4 
        "alphanx0lVN1-PRO", # 4 
        "betaNPvx", # 4 
        "alphapW2nx1Vpnx2", # 4 
        "betaNpxnx1Vpl", # 4 
        "alphaW1ItVad1s2", # 4 
        "betavxDN", # 4 
        "alphaW1nx1Vpl", # 3 
        "alphaW0nx0VPnx1", # 3 
        "betaN0nx0Vnx1pl", # 3 
        "betavxARBPs", # 3 
        "betaARBpx1CONJpx2", # 3 
        "betavxDA", # 3 
        "betanx1CONJARBnx2", # 3 
        "alphaW1nx1VPnx2", # 3 
        "betapuVnxpuvx", # 3 
        "betaN1nx0Vnx1s2", # 3 
        "betasARB", # 3 
        "alphaW0nx0Vnx1s2", # 3 
        "betaN1nx1VP", # 3 
        "betapPU", # 3 
        "alphaW0s0Vs1", # 2 
        "betaN0nx0Vnx1pnx2", # 2 
        "betaVvx-arb", # 2 
        "betaNpxnx0VPnx1", # 2 
        "betaPNss", # 2 
        "betaNpxs0Vnx1", # 2 
        "betaN1nx0VPnx1", # 2 
        "betaNpxnx0Vpl", # 2 
        "betaNpx2nx1Vpnx2", # 2 
        "betaDNax", # 2 
        "betaN1nx1Vp", # 2 
        "betaNpxnx2Vnx1", # 2 
        "alphaW0nx0Vpl", # 2 
        "betaNpx2nx0Vnx1pnx2", # 2 
        "betaN1nx1VPnx2", # 2 
        "alphaW0s0Vnx1", # 2 
        "alphaW1nx1VP", # 2 
        "alphaREGnx1VPnx2", # 2 
        "alphaW2nx0Vnx1s2", # 2 
        "alphaREInx1VA2", # 2 
        "betaN2nx1Vpnx2", # 2 
        "betaNpxItVad1s2", # 2 
        "betaNpxnx0Px1", # 1 
        "betaNpxnx0Vnx1pl", # 1 
        "alphaRnx1VA2", # 1 
        "betaN0nx0Vnx1Pnx2", # 1 
        "betaNpxnx0Vplnx1", # 1 
        "betaNpxnx1Vpnx2", # 1 
        "alphaRW0nx0Vnx1Pnx2", # 1 
        "alphaW0nx0Vax1", # 1 
        "betapunxVnx1puvx", # 1 
        "alphaW0nx0Vnx1Pnx2", # 1 
        "betanxARBPnx", # 1 
        "betaNpxnx1Vs2", # 1 
        "alphaW1InvItVnx1s2", # 1 
        "alphaW0nx0N1s1", # 1 
        "betaN0nx0N1s1", # 1 
        "alphaW0nx0Vnx1pnx2", # 1 
        "alphaW0nx0Vnx1pl", # 1 
        "alphanx0APnx1-PRO", # 1 
        "betaspuARBPs", # 1 
        "betaN2nx0Vnx1pnx2", # 1 
        "alphanx0lVnx2N1", # 1 
        "betaNpxnx1VP", # 1 
        "betaNpxnx0Vnx2nx1", # 1 
        "betaENpxnx1V", # 1 
        "betaNPnxs", # 1 
        "betaN1nx0Vnx1Pnx2", # 1 
        "betaNpxItVnx1s2", # 1 
        "alphaDnx0Vpnx1", # 1 
        "alphaW1nx1Vpnx2", # 1 
        "betaNpx2nx1VPnx2", # 1 
        "betaARBnx1CONJnx2", # 1 
        "alphapW1nx0Vpnx1", # 1 
        "betavxPNs", # 1 
        "betaDApx", # 1 
        "betaNpx1nx0VPnx1", # 1 
        "betaN0nx0lVN1", # 1 
        "betaNpxs0NPnx1", # 1 
        "alphaW1nx0VPnx1", # 1 
    ]
