from __future__ import print_function
from nltk.featstruct import FeatStruct
from nltk.sem.logic import Variable, VariableExpression, Expression

fs = FeatStruct(
    bot=FeatStruct(
        agr=Variable("@A"),
        card=Variable("@G"),
        compar=Variable("@N"),
        compl=Variable("@M"),
        conj=Variable("@F"),
        const=Variable("@H"),
        decreas=Variable("@J"),
        definite=Variable("@K"),
        equiv=Variable("@P"),
        gen=Variable("@L"),
        pron=Variable("@E"),
        quan=Variable("@I"),
        refl=Variable("@B"),
        super=Variable("@O"),
        wh=Variable("@D"),
    ),
    cat='np'
)

fs2 = FeatStruct(
    top=FeatStruct(
        agr=Variable("@A"),
        card=Variable("@G"),
        compar=Variable("@N"),
        compl=Variable("@M"),
        conj=Variable("@F"),
        const=Variable("@H"),
        decreas=Variable("@J"),
        definite=Variable("@K"),
        equiv=Variable("@P"),
        gen=Variable("@L"),
        pron=Variable("@E"),
        quan=Variable("@I"),
        refl=Variable("@B"),
        super=Variable("@O"),
        wh=Variable("@D"),
    ),
    bot=FeatStruct(compar='-'),
    cat='n'
)

print(fs)
print(fs2)
