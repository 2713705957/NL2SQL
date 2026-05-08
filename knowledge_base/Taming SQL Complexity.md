Taming SQL Complexity: LLM-Based Equivalence Evaluation for Text-to-SQL
Qingyun Zeng12 Simin Ma3 Arash Niknafs1 Ashish Basran1 Carol Szabo1
Abstract
The rise of Large Language Models (LLMs) has
significantly advanced Text-to-SQL (NL2SQL)
arXiv:2506.09359v1  [cs.CL]  11 Jun 2025
systems, yet evaluating the semantic equivalence
of generated SQL remains a challenge, especially
given ambiguous user queries and multiple valid
SQL interpretations. This paper explores using
LLMs to assess both semantic and a more prac
tical ”weak” semantic equivalence. We analyze
commonpatterns of SQLequivalenceandinequiv
alence, discuss challenges in LLM-based evalua
tion.
1. Introduction
Text-to-SQL or Natural-Language-to-SQL (NL2SQL) sys
tems, which translate natural language questions into SQL
queries, have become increasingly important in the era of
big data. The rapid advancements in Artificial Intelligence
(AI), particularly with Large Language Models (LLMs) such
as Generative Pretrained Transformer (GPT), have signifi
cantly improved the performance of these systems (Pourreza
&Rafiei, 2024a; Pourreza et al., 2024b;d; Li et al., 2025;
Talaei et al., 2024; Pourreza et al., 2024c; Pourreza & Rafiei,
2024b; Pourreza et al., 2024a). However, a critical challenge
in developing and refining robust NL2SQL systems is the
ability to effectively evaluate the quality of the generated
SQLqueries. While various benchmarks like SPIDER (Yu
et al., 2018) and BIRD (Li et al., 2024) track progress, a
fundamental aspect of evaluation is determining whether a
generated SQL query is semantically equivalent to an ex
pected or reference query. This paper focuses on this core
problem: leveraging LLMs for the nuanced task of SQL
equivalence assessment.
Evaluating SQL equivalence is fraught with difficulties.
*Equal contribution 1Microsoft Copilot Studio AI, Seat
tle, United States 2University of Pennsylvania, Phidelphia,
United States 3Zoom Communications, San Jose, United States
(work done at Microsoft). Correspondence to: Qingyun Zeng
<qze@sas.upenn.edu>.
Proceedings of the 42nd International Conference on Machine
Learning, Vancouver, Canada. PMLR 267, 2025. Copyright 2025
by the author(s).
These stem from the diverse interpretations of ’equivalence’
itself—ranging from strict syntactic identity to broader se
mantic or practical equivalence relevant in real-world ap
plications (Section 3). Traditional metrics like Execution
Accuracy (EX), while widely used, suffer from limitations
such as false positives and negatives, particularly with sparse
test data or when minor syntactic variations are acceptable.
Furthermore, employing LLMs for this task, despite their
advanced reasoning capabilities, introduces its own chal
lenges, including ensuring response consistency, manag
ing the impact of preprocessing, and designing effective
prompts (Section 7).
This paper addresses these challenges by proposing and
evaluating a comprehensive LLM-based framework for SQL
equivalence assessment. First, we systematically character
ize common patterns of both semantically equivalent and
inequivalent SQL queries (Section 4, Appendix B, C). This
provides a structured foundation for developing robust eval
uation methodologies and datasets, and includes distinguish
ing between strict semantic equivalence and a more practical
’weak’ equivalence relevant to business applications like Mi
crosoft Dataverse (Lyu et al., 2020). Second, we develop
and detail an LLM-based evaluation pipeline (Section 7, Ap
pendix E). This pipeline integrates preprocessing, efficient
string-based matching for unambiguous cases, and sophis
ticated LLM reasoning. Key features include a multi-run
strategy to enhance stability and the exploration of advanced
techniques such as query rewriting for subqueries and the
’Miniature & Mull’ prompting strategy (Zhao et al., 2024).
Third, we conduct a thorough experimental evaluation (Sec
tion 8) of our framework using three distinct datasets: a
manually labeled set from the real-world Dataverse environ
ment, a targeted development set for iterative refinement,
and a comprehensive synthetic dataset designed around our
characterized SQL patterns. Our results demonstrate the
effectiveness of LLMs (specifically GPT-4 variants) in this
complex task, quantify the impact of different prompting
strategies and pipeline components, and highlight important
trade-offs for practical application. Ultimately, our work
aims to provide insights and a practical methodology for
improving the reliability of SQL equivalence evaluation,
thereby contributing to the development of more accurate
and trustworthy Text-to-SQL systems.
The remainder of this paper is organized as follows: Sec
1
LLM-Based Equivalence Evaluation for Text-to-SQL
tion 2 reviews related work. Section 3 delves into the
challenges of SQL evaluation. Section 4 characterizes
SQL equivalence patterns, and Section 5 discusses practical
equivalence in business contexts. Section 6 describes our
datasets, while Section 7 details our evaluation framework.
Section 8 presents experimental results. Finally, Section 9
concludes the paper and discusses future directions.
2. Related Work
The evaluation of text-to-SQL (NL2SQL) systems and the
use of LLMs for evaluation have been active areas of re
search. Several studies have focused on various aspects of
this problem.
In early days, the research is mainly focusing on the methods
using formalized proving. For example Cosette ((Chu et al.,
2017), (Chu et al., 2018)) was created as an automated
prover for checking semantic equivalences of SQL queries.
It formalizes a significant portion of SQL within the Coq
Proof Assistant and the Rosette symbolic virtual machine.
For any given pair of queries, it provides either a formal
proof of equivalence or a counterexample. In (Ding et al.,
2023), the author proposed SQLSolver which applied the
Linear Integer Arithmetic and focused more on the semantic
checking rather than syntacic checking.
While the previous methods focused more on the formal
proving methods, (K¨oberlein et al., 2024) established a
graph-based method. It breaks a single SQL down for sev
eral paths from the 0 to the whole SQL, and define quantify
the semantic equivalence using these constructed graphs.
(Zhan et al., 2025) proposed a similar approach. Ascoli et
al. (2024) (Ascoli et al., 2025) critique the two primary
Text-to-SQL evaluation metrics, Execution Accuracy (EX)
and Exact Set Matching (ESM), for their tendency to mis
represent model performance, a problem exacerbated by the
stylistic diversity of Large Language Model outputs. They
introduce a new metric, Enhanced Tree Matching (ETM),
which compares the syntactic and semantic elements of the
predicted and gold SQL queries using their abstract syntax
trees and a set of verifiable equivalence rules, demonstrating
significantly lower false positive and negative rates than
previous metrics.
Though this logic and reasoning based approach is effec
tive, they cannot capture fully the semantic meaning from
the SQL queries, for example, the entities and relations
from the natural language names of the tables and columns,
which usually have rich meaning. As Large Language Mod
els have strong natural language understanding as well as
text generation, especially in code generation (for example,
Codex by OpenAI, CodeLlama by Meta, and Qwen-Coder
by Alibaba), evaluation of various language related tasks
using LLM as judge become more and more popular ((Liu
et al., 2024a), (Chiang & Lee, 2023), (Liu et al., 2024b),
(Wang et al., 2023), etc.) Hence it makes sense to develop
LLM-based evaluator for checking SQL equivalences. For
example, (Zhao et al., 2024) analyzed the performance of
LLM in evaluating semantic equivalence of SQL in gen
eral, LLMs are a promising tool for assisting data analysts
in writing semantically equivalent SQL queries. However,
challenges still persist. Additionally, they offer a better met
ric for evaluating SQL generation than the commonly used
Execution Accuracy(EX).
A concurrent trend in evaluation is the use of Large Lan
guage Models (LLMs) as automated judges, which has been
shown to be effective across many NLP tasks (Gu et al.,
2025). While this approach is also being considered for SQL
evaluation, the nature of LLM-based Text-to-SQL genera
tion presents unique challenges. Previous evaluation meth
ods for checking SQL equivalence often focus on syntactic
or structural aspects of the queries. However, LLM-based
scenarios introduce more difficulties than just checking for
syntactic or semantic equivalence. For instance, a single
natural language question might have several valid inter
pretations, leading to multiple non-equivalent SQL queries
that are all correct. Furthermore, semantically inequivalent
queries may be ”close enough” for practical use, adding
another layer of complexity to the evaluation task.
(Zhao et al., 2024) explore the challenging and theoretically
undecidable problem of determining SQL equivalence using
Large Language Models (LLMs). The authors introduce
LLM-SQL-Solver, a framework designed to test and guide
LLMs in this task by considering both strict semantic equiv
alence and a more practical ”relaxed equivalence.” They pro
pose novel prompting techniques, such as ”Miniature and
Mull” and ”Explain and Compare,” to improve the model’s
reasoning. Their findings show that while LLMs like GPT-4
are promising, they still struggle to correctly identify equiv
alence in complex queries, but their judgments can align
more closely with human preferences for text-to-SQL out
puts than traditional execution accuracy metrics.
On the other hand, we know that LLM is not perfect at
logical reasoning, and tends to hallucinate usually. These
unstable factors bring more issues in evaluating SQLs. One
way to improve the quality of Text-to-SQL is though self
tuning, which needs to use the result of the SQL evaluation
((Pourreza & Rafiei, 2024a), (Zhang et al., 2024)). Hence
the quality of the SQL evaluation becomes a bottleneck in
improving the quality of Text-to-SQL.
Hence, one big chanllenge is to pick good metrics for SQL
evaluation. As pointed by many literature mentioned pre
viously, the usual Exact Match(EM) and Execution Accu
racy(EX) do not suffice to this task. (Kim et al., 2025) pro
posed a newmetric called Expert-level False-Less Execution
(FLEX) which focus on aligning more with human’s eval
2
LLM-Based Equivalence Evaluation for Text-to-SQL
uation preference, and which reduces both false negatives
and false positives in using Execution Accuracy. In practice,
the criteria for ’equivalence’ is essential for building a SQL
equivalence evaluator.
Several open-source projects, such as Defog.ai’s SQL Eval
Tool ((AI, 2024), (defog ai, n.d.)). Defog.ai’s framework
compares SQL outputs based on their ability to correctly
answer database queries, recognizing that different SQL
queries can achieve the same results. It is designed to over
come limitations in using LLMs (like GPT-4) for evalua
tion. Arize ((Dhinakaran & Singh, 2024)) also proposed an
LLM-based evaluation framework for SQL evaluation, and
their approach emphasizes the use of reference SQL queries,
execution-based evaluation, and semantic understanding to
improve benchmarking processes.
3. Challenges in SQL Evaluation
Evaluating the correctness and equivalence of SQL queries
presents significant challenges, stemming from the inherent
complexity of the SQL language, the diversity of database
schemas and states, and the varying expectations of what
constitutes an ”equivalent” or ”correct” query in different
contexts.
3.1. The Nuance of SQL Equivalence
Defining SQL equivalence is not straightforward. Before
discussing different types of equivalence, let’s establish
some foundational concepts:
Definition 3.1 (Parsable). A query is parsable if and only
if (iff) it adheres to SQL syntax and can be parsed into an
Abstract Syntax Tree (AST) representation.
Definition 3.2 (Executable). A query is executable within
a given database schema if and only if (iff) it is parsable
and can be executed on a database of that schema without
errors.
With these in mind, several types of equivalence can be
distinguished, though their practical evaluation varies in
difficulty:
Definition 3.3 (Syntactically Equivalent). Two queries
are syntactically equivalent if and only if (iff) their Abstract
Syntax Tree (AST) representations are identical, perhaps
allowing for trivial differences like whitespace or canonical
ized aliasing.
This is the easiest to check but is often too restrictive, as
many syntactically different queries can produce the same
result. Exact Set Matching (ESM), which performs string
based component-wise matching, is a metric that approxi
mates this.
Definition 3.4 (Semantically Equivalent). Two queries are
semantically equivalent within a given database schema if
and only if (iff) they produce the same result when executed
on an arbitrary but fixed database of that schema.
This is a powerful definition but is notoriously difficult to
verify formally, often being undecidable in the general case.
Proving semantic equivalence typically requires sophisti
cated logical reasoning or symbolic execution techniques,
as explored by tools like Cosette (Chu et al., 2017).
Relaxed or Practical (Weak) Equivalence: In many real
world scenarios, particularly in business intelligence or in
teractive data exploration (e.g., Dataverse QnA (Lyu et al.,
2020)), a less strict notion of equivalence is often acceptable
or even preferred.
Definition 3.5 (Weakly Equivalent). Two SQL queries
are weakly equivalent iff they will most likely produce the
same results given the database in practical use, or if minor,
trivial edits (like changing an alias or the order of indepen
dent conditions) would make them semantically equivalent
according to user intent.
This notion acknowledges that users may prioritize queries
that are ”good enough” or ”useful” for their immediate task,
even if they are not strictly semantically equivalent across all
hypothetical database states. The Text-to-SQL in consumer
applications often fits this category, where some tolerance
for minor semantic inequivalence is permissible.
3.2. Execution Accuracy: A Flawed Proxy for Semantic
Equivalence
Given the difficulty of proving true semantic equivalence,
Execution Accuracy (EX) has become a widely adopted met
ric. EX compares the results of a candidate query against a
gold query when executed on a specific test database. While
practical, EX is an imperfect approximation of semantic
equivalence and suffers from several limitations (see Ap
pendix A for illustrative examples):
• False Positives (FP): An incorrect query might acci
dentally produce the same result as the gold query on
a limited test database. For instance, a query with an
incomplete WHERE clause (e.g., missing a condition
like Salary > 50000 when filtering employees)
might still pass if all relevant records in the test data
happen to satisfy the missing condition. This is partic
ularly problematic when test databases lack diversity
or contain sparse data, where many distinct (and incor
rect) queries might return empty sets, thus appearing
”correct.”
• False Negatives (FN): A semantically correct query
might be marked as incorrect by EX if its output differs
from the gold query’s output in ways that are irrelevant
to the user’s intent. Common examples include differ
ences in column order (when not specified by ORDER
3
LLM-Based Equivalence Evaluation for Text-to-SQL
BY), different column aliases (e.g., TotalOrders vs.
OrderCount), or minor variations in formatting. If
the task does not specify an ordering, a query returning
the correct set of rows in a different order might be
unfairly penalized.
Consequently, EX can underestimate the true ”usefulness”
or ”practical correctness” of a generated SQL query, es
pecially in scenarios where minor syntactic variations are
acceptable as long as the core intent is met. Metrics like
Valid Efficiency Score (VES) (Li et al., 2024) attempt to
address some aspects by considering efficiency alongside
correctness for queries already deemed valid by EX.
3.3. Subjectivity and Context-Dependence in Evaluation
The ”correctness” of a SQL query is often subjective and
highly dependent on the specific application context and
user expectations.
• Benchmarking vs. Business Applications: For aca
demic benchmarking (e.g., datasets like BIRD (Li et al.,
2024)), EX, despite its flaws, is often favored for its
objectivity, reproducibility, and ease of automation. Ef
forts like FLEX (Kim et al., 2025) aim to refine EX to
better align with human preferences by reducing FPs
and FNs.
• In contrast, business applications (e.g., Dataverse QnA,
(Lyu et al., 2020)) may prioritize ”relaxed equivalence.”
The cost of a false negative (rejecting a practically use
ful query) can be higher than a nuanced false positive
(accepting a query with minor, non-critical flaws). The
limited data in test environments for such applications
can exacerbate the FP issue for EX.
3.4. LLMs in SQL Evaluation: Promise and Pitfalls
Large Language Models (LLMs) offer a promising avenue
for more nuanced SQL evaluation, potentially bridging the
gap between strict syntactic/semantic checks and human
like assessment of practical equivalence. LLMs can be
prompted to consider context, schema, and even ”intent”
when comparing queries. However, relying on LLMs for
evaluation introduces its own set of challenges:
• Consistency and Reliability: LLM responses can be
non-deterministic and may vary across runs or with
slight prompt modifications.
• Robustness: While LLMs might align well with hu
man expert preferences in some cases (e.g., as sug
gested by LLM-SQL-Solver (Zhao et al., 2024)), they
are not yet a foolproof substitute for execution-based
checks, especially for ensuring factual correctness.
• Preprocessing Impact: Techniques like replacing spe
cific column selections with * to simplify queries for
LLMevaluation can be a double-edged sword. While
potentially helpful in some Dataverse scenarios by forc
ing focus on broader logic, it can obscure important
differences and may not be suitable for rigorous bench
marking where precise column selection matters.
Therefore, while LLMs can augment SQL evaluation, partic
ularly for assessing ”relaxed equivalence,” their use requires
careful prompt engineering, strategies for ensuring stability
(e.g., multiple runs, self-consistency checks), and an aware
ness of their limitations. The choice of evaluation metric
and methodology must be tailored to the specific require
ments of the Text-to-SQL task, whether it’s for academic
benchmarking or real-world application deployment.
4. Characterizing SQL Semantical
Equivalence for Evaluation
As we have seen, evaluating SQL equivalence is not a deter
ministic problem especially in the text-to-sql context, hence
give a pair of SQL queries with a natural language question,
the equivalence judgment can be subjective and context
dependent. In this section, we should focus on the case of
semantic equivalence case, which should be regarded as a
baseline for all equivalence criteria.
Evaluating SQL equivalence, especially in the text-to-SQL
context, is a nuanced task where judgments can be subjective
and context-dependent. While Execution Accuracy (EX)
offers an approximation for checking semantic equivalence,
it proves insufficient due to challenges like incomplete test
data coverage or practical data scarcity. To address these
limitations and establish a robust baseline for evaluation,
this section focuses on semantic equivalence. We systemati
cally define and categorize common patterns of semantically
equivalent SQL queries and frequent sources of semantic
inequivalence. This detailed characterization is essential for
constructing targeted synthetic datasets, which are invalu
able for training and rigorously testing LLM-based SQL
evaluators. This section outlines common patterns of se
mantically equivalent SQL queries and common sources of
semantic inequivalence, which form the basis for construct
ing targeted evaluation datasets.
4.1. Patterns of Semantically Equivalent SQL Queries
Two SQLqueries can be syntactically different yet seman
tically equivalent. Understanding these variations is key
to developing robust evaluators that do not penalize valid
alternative formulations. Common categories highlight vari
ous ways SQL queries can be equivalent, such as variations
in join usage, methods for handling duplicates, different
join syntaxes, aliasing, date handling, case sensitivity, ag
4
LLM-Based Equivalence Evaluation for Text-to-SQL
gregation techniques, filtering methods, conditional logic,
ordering, and existence checks. A detailed list of these cate
gories is provided in Appendix B. Illustrative SQL examples
for each of these categories are provided in Appendix C.
4.2. Patterns of Semantically Inequivalent SQL Queries
Conversely, queries that appear syntactically similar can be
semantically inequivalent, leading to different results. Iden
tifying these subtle but critical differences is a key challenge
for SQL evaluators. Common sources of inequivalence
include errors in join conditions, WHERE clauses, aggrega
tion, use of DISTINCT/GROUP BY, subquery logic, logical
operators in filters, ORDER BY clauses, and function usage.
Adetailed list of these common sources of inequivalence
is provided in Appendix B. Illustrative SQL examples for
these patterns are also provided in Appendix C.
4.3. Synthetic Dataset Construction for Semantic
Evaluation
The characterization of equivalent and inequivalent SQL
patterns detailed in Sections 4.1 and 4.2 directly informs the
construction of targeted evaluation datasets. Such datasets,
comprising pairs of SQL queries covering a wide range of
these constructs, are invaluable for training and rigorously
testing SQL analysis tools, particularly LLM-based evalua
tors. The specific synthetic dataset developed for this work,
based on these principles to facilitate a granular assessment
of an evaluator’s strengths and weaknesses, is described in
Section 6.
5. Practical SQL Equivalence in Business
Applications
While Section 4 focuses on a systematic characterization
of semantic equivalence, the practical demands of SQL
evaluation in business applications, such as those involving
Dataverse, often necessitate a more nuanced approach. In
these contexts, strict semantic equivalence, while a valu
able theoretical baseline, may not always align with user
needs or the practical utility of a generated query. Business
applications frequently prioritize ”relaxed” or ”practical”
equivalence, where the primary concern is whether a query
fulfills the user’s intent and returns useful results within the
specific operational environment, even if minor syntactic or
semantic deviations exist.
The limitations of Execution Accuracy (EX), as discussed
in Section 3 and illustrated in Appendix A, become partic
ularly salient here. For instance, in a Dataverse scenario,
a False Negative (FN) — where a practically useful query
is rejected due to minor differences like column aliasing
or inconsequential variations in row order — can be more
detrimental than a nuanced False Positive (FP) where a
query, though not perfectly semantically equivalent across
all hypothetical database states, performs correctly on the
typical production data. The cost of rejecting a query that
meets the immediate business need often outweighs the risk
of accepting one with minor, non-critical flaws, especially
when test data is limited.
This contrasts with academic benchmarking environments
like BIRD, where EX, despite its known tendency to un
derestimate true semantic equivalence, is often favored for
its objectivity and reproducibility. In such settings, efforts
are directed towards refining EX (e.g., FLEX (Kim et al.,
2025)) or developing LLM-based methods that can leverage
EX’s strengths while mitigating its weaknesses.
Preprocessing techniques also play a different role depend
ing on the context. In business applications like Dataverse,
simplifying queries for LLM evaluation by, for example,
replacing specific column selections with * can be a prag
matic, albeit ”brutal,” mitigation strategy. This approach
forces the evaluation to focus on the core logic (joins, fil
ters) and can be useful when minor variations in selected
columns are acceptable. However, such preprocessing is
generally unsuitable for rigorous benchmarking scenarios
like BIRD, as it can obscure important semantic differences
and may even cause LLM-based evaluations to regress in
performance compared to standard EX.
Ultimately, the criteria for SQL equivalence and the choice
of evaluation methodology must be carefully tailored to the
specific application. A one-size-fits-all approach is insuffi
cient; business applications may lean towards context-aware,
relaxed equivalence judgments, while academic benchmarks
will continue to demand more stringent, reproducible met
rics. Understanding these differing requirements is crucial
for developing effective SQL evaluation strategies, whether
LLM-based or otherwise.
6. Data
To develop and evaluate our LLM-based SQL equivalence
assessment methodology, we utilized three distinct datasets,
each serving a specific purpose: a manually labeled dataset
from a real-world application (Microsoft Dataverse), a de
velopment dataset for iterative refinement, and a broader
synthetic dataset for semantical equivalence evaluation.
6.1. Manually Labeled Dataverse Dataset
Aprimary dataset was curated from the Dataverse environ
ment, a data platform integral to Dynamics 365 applications.
Queries within Dataverse often present distinct challenges
due to its unique schema design and its integration with
various Dynamics 365 applications, such as Power Apps, Fi
nance and Operations (FnO), Intelligent Order Management
(IOM), and Sales. The construction of this dataset com
5
LLM-Based Equivalence Evaluation for Text-to-SQL
Table 1. Ground truth distribution for Dataverse dataset
GROUND TRUTH
COUNT
TOTAL POSITIVE
TOTAL NEGATIVE
56
21
menced with 77 ground truth examples, each comprising a
natural language query and its corresponding SQL query.
Wethenutilized a GPT-based pipeline to generate alternative
SQLqueries from these natural language questions, lever
aging available schema information. Subsequently, each
pair consisting of an original SQL query and its generated
counterpart was manually evaluated and labeled for logical
equivalence. The resulting distribution of this ground truth
is presented in Table 1.
6.2. Development Dataset
To facilitate the iterative improvement of our evaluation
algorithm and prompt engineering, we created a dedicated
development dataset during the iteration of the evaluation
method. This set comprises 14 query pairs selected from
challenging failure cases and instances of unstable LLM
judgments encountered during internal tests, i.e. each query
comes from a category of difficult patterns that the evalua
tion pipeline cannot get it right. This targeted dataset allows
us to rapidly test hypotheses, fine-tune prompts, and address
specific weaknesses observed in the LLM’s reasoning or our
overall evaluation methodology.
6.3. Synthetic Dataset for Pattern Evaluation
To systematically assess the LLM’s ability to handle a wide
variety of SQL equivalence and inequivalence patterns, as
characterized in Section 4 and detailed in Appendix B, we
constructed a synthetic dataset. This dataset was designed
to cover numerous SQL constructs and common variations.
• Equivalent Pairs: We created 80 pairs of semantically
equivalent queries. These pairs demonstrate different
but logically identical ways to achieve the same result,
encompassing variations such as join types (JOIN vs.
subquery), distinct vs. group by, implicit vs. explicit
join, alias usage, date format differences, case sensi
tivity, aggregation methods, filtering methods, CASE
statements vs. WHERE clauses, ORDER BY clause
variations, and EXISTS vs. JOIN constructs. These
were split into two sub-datasets of 60 and 20 pairs for
different testing phases.
• Inequivalent Pairs: We also constructed 80 pairs of
semantically inequivalent queries. These pairs were
designed to differ in crucial aspects that would lead
to different results when executed, such as incorrect
join conditions, flawed WHERE clauses, erroneous
aggregation, misuse of subqueries, logical errors in
f
iltering with AND/OR, incorrect ORDER BY clauses,
and improper function usage.
This synthetic dataset provides a controlled environment
for evaluating the LLM’s understanding of specific SQL
transformations and potential pitfalls.
7. LLM-Based Evaluation Methodology
Weexperiments the LLM-Based Evaluation Methodology
as the core component for assessing SQL equivalence. In
addition to this, we also using string based methods for
better efficiency. First, we perform a preprocessing which
standardizes SQL formatting issues, for example, date/time,
f
ilter, etc. Next we apply the string-based Exact Match (EM)
and Exact Set Match (ESM) which are slight adapted to the
database that we use. If inequivalence has been determined
from this step, we apply a GPT based evaluation, we lever
age GPT-4-0314, which was the most capable LLM known
for strong natural language understanding and reasoning
capabilities at the time we performed the experiment. In
the later stage we switch to gpt-4-32k-0613 and Our ap
proach involves formulating the SQL equivalence problem
as a natural language inference task. Given a pair of SQL
queries, (SQL1, SQL2), whether SQL1 and SQL2 are logi
cally equivalent or not.
Weutilize a carefully designed prompt that provides clear
instructions to the LLM. The prompt includes the following
elements:
• Task Definition: A clear statement that the task is to
assess the semantic equivalence of two SQL queries.
• Context Setting: Information specifying that the SQL
queries are intended for Dataverse t-sql, used in scenar
ios like PowerApps, Sales, and Finance and Operations,
and highlighting the need to consider optionset/string
f
ilter equivalence.
• SQL Query Pair: The two SQL queries to be com
pared, presented in a clear and formatted manner.
• Schema Information (Optional): Relevant database
schema information, including table names, column
names, data types, and relationships, to provide context
for the LLM.
• Query Execution Results (Optional): The results
obtained from executing the SQL queries against a
database, to aid in determining equivalence.
• Output Format: Instructions specifying the desired
output format, such as a binary classification (Equiva
lent/Not Equivalent) along with a confidence score, or
6
LLM-Based Equivalence Evaluation for Text-to-SQL
a more detailed categorization (Equivalent/Minor Dif
ferences/Significant Differences/Not Equivalent/Other)
and a rationale for the judgment. We also explicitly
ask the model to provide the main reasons for differ
ences (e.g., missing join or wrong filter, etc.) when the
queries are not equivalent.
• Examples(Optional): Few-shot examples demonstrat
ing correct equivalence judgments for various SQL
patterns, to guide the LLM’s reasoning process.
Weexperiment with different prompt variations to optimize
performance. A basic version of the prompt template used
is shown in Appendix D.
To account for the inherent non-determinism in LLM re
sponses, we implemented a multi-run strategy for evalua
tion: 1. For each query pair, the LLM is run multiple times
(e.g., 3 by default). 2. If the model consistently produces
the same judgment (all Equivalent or all Not Equivalent),
that is taken as the final decision. 3. If judgments vary, the
result is classified as ”unstable,” and the number of runs
may be increased (e.g., to 5), applying majority voting to
obtain a more robust result.
8. Experiments
8.1. Experimental Setup
We use the datasets described in Section 6, consisting of
pairs of SQL queries representing both equivalent and in
equivalent cases. We conducted the experiments using GPT
4 series models accessed through the Azure OpenAI API.
Weevaluate the performance of the LLMs using the follow
ing standard metrics:
• Accuracy: Thepercentage of query pairs for which the
LLMcorrectly identifies equivalence or inequivalence.
• Precision: The percentage of query pairs identified
as equivalent by the LLM that are truly equivalent
(according to our ground truth).
• Recall: The percentage of truly equivalent query pairs
(according to our ground truth) that are correctly iden
tified as equivalent by the LLM.
• F1-score: The harmonic mean of precision and recall,
providing a single measure that balances both.
Beside these standard metrics, more importantly, we also
consider
• Stability: The percentage of query pairs for which the
LLMproduces consistent judgments across multiple
runs.
Table 2. Metrics for GPT-4-0314 evaluation compared to ground
truth
LABEL
PRECISION RECALL F1 SCORE
EQUIVALENT
NOT EQUIVALENT
0.9545
0.6429
0.8936
0.8182
0.9231
0.7200
Table 3. Metrics for string based comparison
LABEL
PRECISION RECALL F1 SCORE
EQUIVALENT
NOT EQUIVALENT
1.0000
0.4565
0.5536
1.0000
0.7126
0.6269
• Error Analysis: We categorize the incorrect predic
tions made by the LLM to identify common error
patterns and areas for improvement in the evaluation
methodology or prompt design.
In addition, we qualitatively analyze the rationales provided
by the LLMto understand its reasoning process and identify
potential sources of error.
8.2. Experiment results
8.2.1. BASIC EVALUATION PIPELINE
We first evaluate the basic evaluation pipeline using the
manually labeled Dataverse dataset. The results are sum
marized in Table 2.We describe our evaluation pipeline in
Algorithm 1. We first perform preprocessing and string
based checks for efficiency. If these initial checks do not
determine equivalence, we employ an LLM-based approach.
Wenotioced that LLM-based evaluation have high precision
and recall on equivalent SQL queries but perform slightly
worse on inequivalent ones. Even this seems not good at
the begining, in fact, in practice we acutally have much less
wrong SQL queries from text-to-SQL pipeline hence we
need less checking on the inequivalent ones. Hence this
evaluation pipeline results are robust enough especially for
the debugging purpose. Also, string-based methods has
100% precision on equivalent cases and 100% recall on non
equivalent cases which is by its design. In addition we see
its recall for equivalent cases is not bad (0.5536) on this
data, which means that it can save around 50% of GPT calls
on datasets which have similar distribution as the testing
data we used.
8.2.2. ITERATIONS ON THE PIPELINE
After multiple iteratiosn of the evaluation pipeline dur
ing model updates and quality control of the text-to-SQL
pipeline, we are able to acheive 100% precision and recall
on the original testing data. On the other hands, we summa
7
LLM-Based Equivalence Evaluation for Text-to-SQL
Table 4. Evaluating Semantic Equivalence on Synthetic Data: Ini
tial vs. New Pipeline (both use GPT-4o in LLM part)
DATASET TYPE PASSING RATE PASSING RATE
(INITIAL)
(NEW)
EQUIVALENT
IN-EQUIVALENT
61.25%
90%
95%
83.75%
rized the failure cases into 14 categories and create a small
development data which consists of one data for each cate
gory since we found the pipeline is consistent from small
variations in each category. The dev dataset contains 14
queries. The major reason of failure is also recorded, for
example, missing join, wrong filter, etc.
Weuse the dev data to tune the evaluation algorithm. The
main improvement is on 1) more clear definition of equiva
lence criteria, 2) using Chain-of-Thought fewshot examples,
3) more detailed criteria on the grading. The prompt ex
ample can be found at Appendix D. After the tuning, e got
92.9% accuracy on this data.
8.2.3. IMPROVEMENT ON EVALUATING SEMANTIC
EQUIVALENCE
The evaluation strategy we experimented so far are more on
the practical purpose of equivalences (or weak equivalence)
due to the nature of the text-to-SQL pipeline we used. It
is also useful to have another pipeline which have better
capabilities on determine semantic equivalence which can
1) provide additional insight on the SQL query quality, 2)
can better generalized to other applications.
Weinitially evaluated an improved evaluation pipeline (Al
gorithm 1) on the synthetic data. Based on the failure cases
from this initial evaluation, we observed that many issues
arose from subqueries, where GPT had difficulties translat
ing between SQL queries using subqueries and those using
joins. This led us to experiment with a query-rewrite mod
ule, which rewrites subqueries (if they appear) into queries
with left joins.
Furthermore, we incorporated the Miniature & Mull prompt
ing strategy developed in (Zhao et al., 2024). In this strategy,
LLMsareinstructed to simulate executing both SQL queries
on a self-conceptualized simple database, then repeat this
on a modified version of that database, comparing outputs to
infer equivalence. This prompting strategy has been shown
to be effective for determining semantic equivalence.
The combined effect of these enhancements (query-rewrite
and Miniature & Mull prompting, as described in Algo
rithm 2) on the synthetic dataset is shown in Table 4.
Wehave a significant improvement in equivalent cases, but
slight drop in the in-equivalent case, which implies that we
need to be careful when applying query re-write as it may
cause regressions in some cases.
9. Conclusion
This paper investigated the complex challenge of evaluating
SQL equivalence, a critical task in the development and
refinement of Text-to-SQL systems. We delineated various
notions of equivalence, from strict semantic identity to more
practical, context-dependent interpretations relevant in busi
ness applications like Dataverse. Our work systematically
characterized common patterns of both semantically equiva
lent and inequivalent SQL queries, providing a foundation
for building robust evaluation datasets and methodologies.
We presented an LLM-based evaluation framework that
combines preprocessing, efficient string-based matching,
and sophisticated LLM reasoning, including a multi-run
strategy to manage output variability. Experiments were con
ducted using manually labeled Dataverse queries, a targeted
development set, and a comprehensive synthetic dataset
designed to test various equivalence patterns.
Our findings demonstrate that LLMs, particularly GPT-4,
can achieve high accuracy in assessing SQL equivalence.
Prompt engineering, including the provision of schema in
formation and few-shot examples, proved crucial for enhanc
ing performance, especially for domain-specific nuances
like those in Dataverse. We explored advanced techniques,
such as query rewriting for subqueries and the ”Miniature
&Mull” prompting strategy, which significantly improved
the identification of equivalent query pairs (from 61.25% to
95% on our synthetic dataset), though a slight regression
was observed for inequivalent pairs, highlighting the need
for careful application of such transformations. Our ini
tial pipeline also showed strong performance on real-world
Dataverse queries, particularly in precision for equivalent
cases.
Despite these advancements, challenges remain, including
handling highly complex queries, ensuring consistent LLM
behavior, and mitigating issues arising from preprocessing
steps. Future work should focus on more advanced LLM
reasoning techniques, robust automated query rewriting,
and strategies to reduce LLM hallucination. Further explo
ration into integrating diverse evaluation methods (syntactic,
semantic, execution-based) and leveraging open-source eval
uation tools will also be beneficial. Expanding datasets with
more diverse and complex examples, particularly from real
world applications, and refining error analysis will be key
to advancing the state-of-the-art in SQL equivalence evalua
tion, ultimately contributing to more reliable and effective
Text-to-SQL systems.
8
LLM-Based Equivalence Evaluation for Text-to-SQL
References
AI, D.
Open-sourcing sql eval: Making bench
marking easier for sql generation models, Novem
ber 2024.
URL https://defog.ai/blog/
open-sourcing-sqleval. Accessed: 2024-12-03.
Ascoli, B. G., Kandikonda, Y. S. R., and Choi, J. D. Etm:
Modern insights into perspective on text-to-sql evaluation
in the age of large language models, 2025. URL https:
//arxiv.org/abs/2407.07313.
Chiang, C.-H. and Lee, H.-y. Can large language mod
els be an alternative to human evaluations? In Pro
ceedings of the 61st Annual Meeting of the Association
for Computational Linguistics (Volume 1: Long Papers),
pp. 15607–15631, Toronto, Canada, July 2023. Asso
ciation for Computational Linguistics. URL https:
//aclanthology.org/2023.acl-long.870.
Chu, S., Wang, C., Weitz, K., and Cheung, A. Cosette: An
automated prover for sql. In Conference on Innovative
Data Systems Research, 2017. URL https://api.
semanticscholar.org/CorpusID:12408033.
Chu, S., Cheung, A., and Suciu, D. Axiomatic founda
tions and algorithms for deciding semantic equivalences
of sql queries. Proc. VLDB Endow., 11:1482–1495,
2018. URL https://api.semanticscholar.
org/CorpusID:44183892.
defog ai. sql-eval, n.d. URL https://github.com/
defog-ai/sql-eval. Accessed: 2024-12-03.
Dhinakaran, A. and Singh, M. Text-to-SQL: eval
uating SQL generation with LLM as a judge,
2024.
URL https://arize.com/blog/
of the Nations of the Americas Chapter of the Asso
ciation for Computational Linguistics: Human Lan
guage Technologies (Volume 1: Long Papers), pp. 4448
4475, Albuquerque, New Mexico, April 2025. Asso
ciation for Computational Linguistics. ISBN 979
8-89176-189-6.
doi: 10.18653/v1/2025.naacl-long.
228. URL https://aclanthology.org/2025.
naacl-long.228/.
K¨oberlein, L., Probst, D., and Lenz, R. Quantifying se
mantic query similarity for automated linear sql grad
ing: A graph-based approach, 2024. URL https:
//arxiv.org/abs/2403.14441.
Li, J., Hui, B., Qu, G., Yang, J., Li, B., Li, B., Wang, B., Qin,
B., Geng, R., Huo, N., et al. Can llm already serve as a
database interface? a big bench for large-scale database
grounded text-to-sqls. Advances in Neural Information
Processing Systems, 36, 2024.
Li, R., Feng, Y., Fan, Z., Carenini, G., Zhang, W., Pourreza,
M., and Zhang, Y. DeTriever: Decoder-representation
based retriever for improving NL2SQL in-context learn
ing. In Rambow, O., Wanner, L., Apidianaki, M., Al
Khalifa, H., Eugenio, B. D., and Schockaert, S. (eds.),
Proceedings of the 31st International Conference on Com
putational Linguistics, pp. 8173–8183, Abu Dhabi, UAE,
January 2025. Association for Computational Linguis
tics. URL https://aclanthology.org/2025.
coling-main.544/.
Liu, Y., Yang, T., Huang, S., Zhang, Z., Huang, H., Wei,
F., Deng, W., Sun, F., and Zhang, Q. Calibrating LLM
based evaluator. In Calzolari, N., Kan, M.-Y., Hoste,
V., Lenci, A., Sakti, S., and Xue, N. (eds.), Proceed
ings of the 2024 Joint International Conference on Com
text-to-sql-evaluating-sql-generation-with-llm-as-a-judge/.
Accessed: 2024-12-03.
Ding, H., Wang, Z., Yang, Y., Zhang, D., Xu, Z., Chen,
H., Piskac, R., and Li, J. Proving query equivalence
using linear integer arithmetic. Proc. ACM Manag. Data,
1(4), December 2023. doi: 10.1145/3626768. URL
https://doi.org/10.1145/3626768.
Gu, J., Jiang, X., Shi, Z., Tan, H., Zhai, X., Xu, C., Li,
W., Shen, Y., Ma, S., Liu, H., Wang, S., Zhang, K.,
Wang, Y., Gao, W., Ni, L., and Guo, J. A survey on
llm-as-a-judge, 2025. URL https://arxiv.org/
abs/2411.15594.
Kim, H., Taeyang, J., Choi, S., Choi, S., and Cho, H.
FLEX: Expert-level false-less EXecution metric for text
to-SQL benchmark. In Chiruzzo, L., Ritter, A., and
Wang, L. (eds.), Proceedings of the 2025 Conference
putational Linguistics, Language Resources and Evalu
ation (LREC-COLING 2024), pp. 2638–2656, Torino,
Italia, May 2024a. ELRA and ICCL. URL https:
//aclanthology.org/2024.lrec-main.237.
Liu, Y., Yang, T., Huang, S., Zhang, Z., Huang, H., Wei, F.,
Deng, W., Sun, F., and Zhang, Q. HD-eval: Aligning large
language model evaluators through hierarchical criteria
decomposition. In Ku, L.-W., Martins, A., and Srikumar,
V. (eds.), Proceedings of the 62nd Annual Meeting of
the Association for Computational Linguistics (Volume
1: Long Papers), pp. 7641–7660, Bangkok, Thailand,
August 2024b. Association for Computational Linguistics.
doi: 10.18653/v1/2024.acl-long.413. URL https://
aclanthology.org/2024.acl-long.413.
Lyu, Q., Chakrabarti, K., Hathi, S., Kundu, S., Zhang, J., and
Chen, Z. Hybrid ranking network for text-to-sql, 2020.
URLhttps://arxiv.org/abs/2008.04759.
9
LLM-Based Equivalence Evaluation for Text-to-SQL
Pourreza, M. and Rafiei, D. Din-sql: decomposed in-context
learning of text-to-sql with self-correction. In Proceed
ings of the 37th International Conference on Neural In
formation Processing Systems, NIPS ’23, Red Hook, NY,
USA, 2024a. Curran Associates Inc.
Pourreza, M. and Rafiei, D. DTS-SQL: Decomposed
text-to-SQL with small large language models. In
Al-Onaizan, Y., Bansal, M., and Chen, Y.-N. (eds.),
Findings of the Association for Computational Linguis
tics: EMNLP 2024, pp. 8212–8220, Miami, Florida,
USA, November 2024b. Association for Computational
Linguistics.
doi: 10.18653/v1/2024.findings-emnlp.
481. URL https://aclanthology.org/2024.
findings-emnlp.481/.
Pourreza, M., Li, H., Sun, R., Chung, Y., Talaei, S., Kakkar,
G. T., Gan, Y., Saberi, A., Ozcan, F., and Arik, S. O.
Chase-sql: Multi-path reasoning and preference opti
mized candidate selection in text-to-sql, 2024a. URL
https://arxiv.org/abs/2410.01943.
Pourreza, M., Li, H., Sun, R., Chung, Y., Talaei, S., Kakkar,
G. T., Gan, Y., Saberi, A., Ozcan, F., and Arik, S. O.
Chase-sql: Multi-path reasoning and preference opti
mized candidate selection in text-to-sql, 2024b. URL
https://arxiv.org/abs/2410.01943.
Pourreza, M., Rafiei, D., Feng, Y., Li, R., Fan, Z., and
Zhang, W. Sql-encoder: Improving nl2sql in-context
learning through a context-aware encoder, 2024c. URL
https://arxiv.org/abs/2403.16204.
Pourreza, M., Sun, R., Li, H., Miculicich, L., Pfister, T.,
and Arik, S. O. Sql-gen: Bridging the dialect gap for
text-to-sql via synthetic data and model merging, 2024d.
URLhttps://arxiv.org/abs/2408.12733.
Talaei, S., Pourreza, M., Chang, Y.-C., Mirhoseini, A., and
Saberi, A. Chess: Contextual harnessing for efficient sql
synthesis, 2024. URL https://arxiv.org/abs/
2405.16755.
Wang, J., Liang, Y., Meng, F., Sun, Z., Shi, H., Li, Z.,
Xu, J., Qu, J., and Zhou, J. Is ChatGPT a good NLG
evaluator? a preliminary study. In Dong, Y., Xiao,
W., Wang, L., Liu, F., and Carenini, G. (eds.), Proceed
ings of the 4th New Frontiers in Summarization Work
shop, pp. 1–11, Singapore, December 2023. Association
for Computational Linguistics. doi: 10.18653/v1/2023.
newsum-1.1. URL https://aclanthology.org/
2023.newsum-1.1.
Yu, T., Zhang, R., Yang, K., Yasunaga, M., Wang, D.,
Li, Z., Ma, J., Li, I., Yao, Q., Roman, S., Zhang, Z.,
and Radev, D. Spider: A large-scale human-labeled
dataset for complex and cross-domain semantic pars
ing and text-to-SQL task. In Riloff, E., Chiang, D.,
Hockenmaier, J., and Tsujii, J. (eds.), Proceedings of
the 2018 Conference on Empirical Methods in Natu
ral Language Processing, pp. 3911–3921, Brussels, Bel
gium, October-November 2018. Association for Compu
tational Linguistics. doi: 10.18653/v1/D18-1425. URL
https://aclanthology.org/D18-1425.
Zhan, Y., Cui, L., Weng, H., Wang, G., Tian, Y., Liu, B.,
Yang, Y., Yin, X., Xie, J., and Sun, Y. Towards database
free text-to-SQL evaluation: A graph-based metric for
functional correctness. In Rambow, O., Wanner, L., Apid
ianaki, M., Al-Khalifa, H., Eugenio, B. D., and Schock
aert, S. (eds.), Proceedings of the 31st International Con
ference on Computational Linguistics, pp. 4586–4610,
Abu Dhabi, UAE, January 2025. Association for Compu
tational Linguistics. URL https://aclanthology.
org/2025.coling-main.308/.
Zhang, X., Peng, B., Tian, Y., Zhou, J., Zhang, Y., Mi, H.,
and Meng, H. Self-tuning: Instructing llms to effectively
acquire new knowledge through self-teaching, 2024. URL
https://arxiv.org/abs/2406.06326.
Zhao, F., Lim, L., Ahmad, I., Agrawal, D., and Abbadi,
A. E. Llm-sql-solver: Can llms determine sql equiv
alence?, 2024. URL https://arxiv.org/abs/
2312.10321.
10
LLM-Based Equivalence Evaluation for Text-to-SQL
A. SQLEquivalence Examples (Illustrative)
This appendix provides concrete examples illustrating some of the challenges in SQL evaluation discussed in Section 3.
A.1. Examples of False Positives (FP) in Execution Accuracy
A.1.1. INCOMPLETE WHERE CLAUSE
Scenario: You have a table Employees with columns EmployeeID, Name, Department, and Salary. The task is
to write a SQL query to retrieve employees from the ’Sales’ department who earn more than $50,000.
Correct Query:
SELECT EmployeeID, Name, Department, Salary
FROM Employees
WHERE Department = ’Sales’ AND Salary > 50000;
Incorrect Query (Potential FP):
SELECT EmployeeID, Name, Department, Salary
FROM Employees
WHERE Department = ’Sales’;
Reason for False Positive: If, in the specific test database, all employees in the ’Sales’ department coincidentally earn more
than $50,000, the incorrect query will return the same result set as the correct query. EX would mark the incorrect query as
correct.
A.2. Examples of False Negatives (FN) in Execution Accuracy
A.2.1. UNORDERED RESULT SET
Scenario: Retrieve all products from a Products table (columns: ProductID, ProductName, Price) without any
specific order.
User’s Correct Query:
SELECT ProductID, ProductName, Price
FROM Products;
System’s Expected Query (Implicitly Ordered): Assume the system’s gold query, or the test execution environment,
implicitly orders by ProductID due to table structure or default behavior, even if not specified.-- (Output might be implicitly ordered by ProductID)
SELECT ProductID, ProductName, Price
FROM Products;
Reason for False Negative: If the user’s query returns the correct rows but in a different order (e.g., ordered by
ProductName or insertion order), EX would mark it as incorrect because the raw output doesn’t match the (implicitly
ordered) gold standard, even though the user’s query fulfills the request.
A.2.2. ALIAS OR COLUMN NAME DIFFERENCES
Scenario: Retrieve the total number of orders from the Orders table.
User’s Correct Query:
SELECT COUNT(*) AS TotalOrders
FROM Orders;
System’s Expected Query:
SELECT COUNT(*) AS OrderCount
FROM Orders;
11
LLM-Based Equivalence Evaluation for Text-to-SQL
Reason for False Negative: Both queries correctly calculate the total number of orders. However, EX, if performing a
strict comparison of column names in the result set, would deem the user’s query incorrect due to the difference in aliases
(TotalOrders vs. OrderCount), even though the numerical result is identical and correct.
A.3. Example of Relaxed/Practical Equivalence
Scenario: ”What are the top 3 restaurants in New York?” Assume a restaurants table with columns like id, name,
city, rating.
Query 1 (Considered Practically Equivalent to Query 2):-- Query 1
SELECT name
FROM restaurants
WHERE city = ’New York’
GROUP BY name
ORDER BY AVG(rating) DESC
LIMIT 3;
Query 2 (Considered Practically Equivalent to Query 1):-- Query 2 (using ordinal for ORDER BY)
SELECT name, AVG(rating)
FROM restaurants
WHERE city = ’New York’
GROUP BY 1-- Corresponds to name
ORDER BY 2 DESC-- Corresponds to AVG(rating)
LIMIT 3;
Reason for Practical Equivalence: While syntactically different (Query 2 selects an additional column AVG(rating)
and uses ordinal positions in GROUP BY and ORDER BY), both queries aim to identify the top 3 restaurants by average
rating in New York. In many practical scenarios, especially for data exploration, either query would be acceptable if they
return the same list of restaurant names in the correct order, even if one provides the average rating explicitly and the other
doesn’t. Strict semantic equivalence might be debatable depending on whether the selected columns must be identical, but
for user intent, they are often treated as equivalent.
B. Categorization of SQL Equivalence and Inequivalence Patterns
This appendix details the categories of semantically equivalent and inequivalent SQL query patterns discussed in Section 4.
B.1. Patterns of Semantically Equivalent SQL Queries
The following categories highlight common ways SQL queries can be equivalent:
• Join vs. Subquery: Queries using JOIN clauses can often be rewritten using subqueries (and vice-versa) to achieve the
same result, particularly for relating data across tables.
• Distinct vs. Group By: Both DISTINCT and GROUP BY can be used to eliminate duplicate rows. If no aggregate
functions are needed, these can be interchangeable for uniqueness.
• Implicit vs. Explicit Join: Older SQL syntax sometimes uses implicit joins (comma-separated tables in FROM, join
conditions in WHERE), while modern SQL prefers explicit JOIN syntax. Both can define the same relational algebra
operations.
• Using Alias vs. Full Table Name: Employing table aliases (e.g., SELECT e.name FROM employees e) versus
using full table names does not change the query’s semantics.
• Different Date Formats/Functions: SQL queries might use different functions or string manipulations to handle or
compare date values (e.g., SUBSTRING, strftime, CAST), which can yield equivalent results if the underlying date
logic is the same.
12
LLM-Based Equivalence Evaluation for Text-to-SQL
• Case Sensitivity and Formatting Differences: String comparisons might use functions like LOWER() or UPPER()
to ensure case-insensitivity, or use different but equivalent LIKE patterns. These variations can be semantically
equivalent in terms of the intended match.
• Aggregation Methods: Different but mathematically equivalent ways of specifying aggregations (e.g., SUM(amount)
within a group vs. a correlated subquery for summing) can produce the same aggregated results.
• Filtering Methods: The same logical filter can sometimes be expressed in multiple ways, for instance, using OR versus
UNION for combining conditions on the same table.
• CASEvs. Multiple WHERE Clauses (with UNION): Conditional logic using a CASE statement to derive a column
can sometimes be equivalently expressed using multiple SELECT statements combined with UNION ALL and WHERE
clauses.
• ORDERBYClauses: Trivial differences in ORDER BY (e.g., ORDER BY price DESC vs. ORDER BY price
*-1fornumeric types, assuming positive prices) might result in the same ordering. However, this category requires
careful consideration as not all syntactic variations are semantically equivalent for ordering.
• EXISTSvs. JOIN:Checkingfortheexistence of related records using EXISTS in a subquery can often be equivalently
formulated using a JOIN (typically with DISTINCT if the main table’s rows might be duplicated by the join).
B.2. Patterns of Semantically Inequivalent SQL Queries
The following list details common sources of inequivalence:
• Incorrect JOIN Conditions: Using the wrong columns for a join or an incorrect join type (INNER, LEFT, etc.)
fundamentally changes how tables are related.
• Incorrect WHEREClauses: Errors in filtering logic, such as using > instead of >=, or incorrect Boolean combinations
(AND vs. OR), lead to different subsets of data.
• Incorrect Aggregation: Using the wrong aggregate function (e.g., AVG instead of SUM) or incorrect GROUP BY
columns results in erroneous summary statistics.
• Misuse of DISTINCT and GROUPBY:Applying DISTINCTinappropriately or grouping by too few/many columns
can lead to incorrect uniqueness or aggregation.
• Incorrect Subqueries: Flaws in subquery logic, such as incorrect correlation, filtering, or returning an unexpected
number of rows (e.g., a scalar subquery returning multiple rows), cause errors or incorrect results.
• Incorrect Filtering with AND/OR: Logical errors in combining conditions with AND and OR operators.
• Incorrect ORDER BY Clauses: Sorting by the wrong column or using the wrong sort direction (ASC vs. DESC)
changes the presentation of results, which is semantically different if order matters.
• Misuse of Functions: Applying an incorrect function (e.g., LENGTH vs. CHAR
LENGTH if they behave differently in
the specific SQL dialect for certain character sets) or using function arguments incorrectly.
C. Examples of SQL Equivalence and Inequivalence Patterns
This appendix provides concrete SQL examples for the categories of semantically equivalent and inequivalent SQL queries
discussed in Section 4.
C.1. Patterns of Semantically Equivalent SQL Queries
C.1.1. JOIN VS. SUBQUERY
This category highlights the interchangeable use of JOIN clauses and subqueries. A JOIN directly combines data from
multiple tables based on a related column, while a subquery uses a nested query within the main query. Often, a query
can be written using either approach, although performance may vary. Subqueries can be easier to understand for simple
relationships, while joins are generally preferred for more complex queries involving multiple tables.
13
LLM-Based Equivalence Evaluation for Text-to-SQL
Query: Find the names of all departments with at least one employee.
SQL1:
SELECT dname FROM dept WHERE deptno IN (SELECT deptno FROM emp);
SQL2:
SELECT dname FROM dept d JOIN emp e ON d.deptno = e.deptno GROUP BY dname;
Query: List all customers who have placed an order.
SQL1:
SELECT customer_name FROM customers WHERE customer_id IN (SELECT customer_id FROM
→ orders);
SQL2:
SELECT DISTINCT customer_name FROM customers JOIN orders ON customers.customer_id =
→ orders.customer_id;
C.1.2. DISTINCT VS. GROUP BY
Both DISTINCT and GROUPBYcaneliminate duplicate rows. DISTINCT simply returns unique rows based on all selected
columns. GROUP BY groups rows based on specified columns and allows aggregate functions (like COUNT, SUM, AVG)
to be applied to each group. If you only need to remove duplicates without any aggregation, DISTINCT is simpler. GROUP
BYis necessary when you need to perform calculations within groups.
Query: Get the unique list of product categories.
SQL1:
SELECT DISTINCT category FROM products;
SQL2:
SELECT category FROM products GROUP BY category;
Query: List all unique job titles in the company.
SQL1:
SELECT DISTINCT job_title FROM employees;
SQL2:
SELECT job_title FROM employees GROUP BY job_title;
C.1.3. IMPLICIT VS. EXPLICIT JOIN
Implicit joins (using comma-separated tables in the WHERE clause) are an older syntax. Explicit joins (using JOIN, LEFT
JOIN, RIGHT JOIN, etc.) are the modern, preferred syntax. Explicit joins are more readable and offer clearer control over
the join conditions.
C.1.4. USING ALIAS VS. FULL TABLE NAME
Aliases are shortcuts for table names (e.g., emp e). They make queries shorter and easier to read, especially with long table
names or self-joins. While using full table names is perfectly valid, aliases are generally recommended for clarity.
C.1.5. DIFFERENT DATE FORMAT
This category illustrates different techniques to work with dates, including string manipulation (SUBSTRING, LIKE), date
functions (strftime), and casting (CAST). The best approach depends on the database system and the specific task. Using
dedicated date functions often provides better performance and handles different date formats more reliably.
14
LLM-Based Equivalence Evaluation for Text-to-SQL
C.1.6. CASE SENSITIVITY AND OTHER FORMATTING DIFFERENCES
This category demonstrates different techniques for handling case sensitivity in string comparisons using functions like
LOWERandUPPER.Using these functions ensures consistent results regardless of the case of the data in the database. It
also shows examples of using LIKE and GLOB operators with wildcard characters (%, ) for pattern matching, highlighting
the importance of accounting for variations in string formatting.
C.1.7. AGGREGATION METHODS
Using different aggregation methods to achieve the same result.
Query: Get the total sales amount for each customer.
SQL1:
SELECT customer_id, SUM(amount) as total_sales FROM sales GROUP BY customer_id;
SQL2:
SELECT customer_id, (SELECT SUM(amount) FROM sales s WHERE s.customer_id =
→ sales.customer_id) as total_sales FROM sales GROUP BY customer_id;
Query: Find the average salary for each department.
SQL1:
SELECT dept_id, AVG(salary) as avg_salary FROM employees GROUP BY dept_id;
SQL2:
SELECT dept_id, (SELECT AVG(salary) FROM employees e WHERE e.dept_id =
→ employees.dept_id) as avg_salary FROM employees GROUP BY dept_id;
C.1.8. FILTERING METHODS
Using different filtering methods to achieve the same result.
Query: Retrieve all products that are either in category ’Electronics’ or cost more than $100.
SQL1:
SELECT * FROM products WHERE category = ’Electronics’ OR price > 100;
SQL2:
SELECT * FROM products WHERE category = ’Electronics’
UNION
SELECT * FROM products WHERE price > 100;
Query: Get all employees who work in ’HR’ or ’Finance’.
SQL1:
SELECT * FROM employees WHERE dept = ’HR’ OR dept = ’Finance’;
SQL2:
SELECT * FROM employees WHERE dept = ’HR’
UNION
SELECT * FROM employees WHERE dept = ’Finance’;
15
LLM-Based Equivalence Evaluation for Text-to-SQL
C.1.9. CASE VS. MULTIPLE WHERE CLAUSES
Using CASE statements versus multiple WHERE clauses (typically with UNION) to achieve the same result.
Query: Get the employee names and their status (Active/Inactive).
SQL1:
SELECT name, CASE WHEN active = 1 THEN ’Active’ ELSE ’Inactive’ END as status FROM
→ employees;
SQL2:
SELECT name, ’Active’ as status FROM employees WHERE active = 1
UNION ALL
SELECT name, ’Inactive’ as status FROM employees WHERE active = 0;
Query: Find the products with their availability status (In Stock/Out of Stock).
SQL1:
SELECT product_name, CASE WHEN stock > 0 THEN ’In Stock’ ELSE ’Out of Stock’ END as
→ availability FROM products;
SQL2:
SELECT product_name, ’In Stock’ as availability FROM products WHERE stock > 0
UNION ALL
SELECT product_name, ’Out of Stock’ as availability FROM products WHERE stock = 0;
C.1.10. ORDER BY CLAUSES
Using different ORDER BY clauses to achieve the same result. (This can be tricky and highly dependent on data types and
specific SQL dialect features).
Query: List all products ordered by price from highest to lowest.
SQL1:
SELECT * FROM products ORDER BY price DESC;
SQL2(Illustrative, may not be universally equivalent or good practice):
SELECT * FROM products ORDER BY price *-1 ASC;
Query: Get all employees ordered by their hire date from most recent to oldest.
SQL1:
SELECT * FROM employees ORDER BY hire_date DESC;
SQL2(Illustrative, highly dialect-specific if negative sign works on dates):-- SELECT * FROM employees ORDER BY-hire_date;-- This syntax is not standard SQL for dates and might not work or might have
→ unintended behavior.-- A more robust equivalent would be identical to SQL1 or rely on specific date
→ functions if available.-- For illustration, if hire_date was a numeric representation (e.g., epoch seconds),
→ then ORDER BY-hire_date could work.
16
LLM-Based Equivalence Evaluation for Text-to-SQL
C.1.11. EXISTS VS. JOIN
Using EXISTS versus JOIN clauses to achieve the same result.
Query: Find customers who have placed at least one order.
SQL1:
SELECT customer_name FROM customers WHERE EXISTS (SELECT 1 FROM orders WHERE
→ customers.customer_id = orders.customer_id);
SQL2:
SELECT DISTINCT c.customer_name
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id;
Query: Get the names of students who are enrolled in any course.
SQL1:
SELECT student_name FROM students WHERE EXISTS (SELECT 1 FROM enrollments WHERE
→ students.student_id = enrollments.student_id);
SQL2:
SELECT DISTINCT s.student_name
FROM students s
JOIN enrollments e ON s.student_id = e.student_id;
C.2. Patterns of Semantically Inequivalent SQL Queries
C.2.1. INCORRECT JOIN CONDITIONS
Using incorrect or incomplete JOIN conditions that lead to incorrect results.
Query: Retrieve all orders with their corresponding customer names.
SQL1(Correct):
SELECT orders.order_id, customers.customer_name
FROM orders
INNER JOIN customers ON orders.customer_id = customers.customer_id;
SQL2(Incorrect):
SELECT orders.order_id, customers.customer_name
FROM orders
INNER JOIN customers ON orders.order_id = customers.customer_id;-- Incorrect join key
C.2.2. INCORRECT WHERE CLAUSES
Using incorrect or incomplete WHERE clauses that filter results incorrectly.
Query: Find all products that cost more than $100.
SQL1(Correct):
SELECT * FROM products WHERE price > 100;
SQL2(Incorrect):
SELECT * FROM products WHERE price >= 100;-- Incorrect operator
17
LLM-Based Equivalence Evaluation for Text-to-SQL
C.2.3. INCORRECT AGGREGATION
Using incorrect aggregation functions or grouping that lead to incorrect results.
Query: Get the total sales amount for each customer.
SQL1(Correct):
SELECT customer_id, SUM(amount) as total_sales
FROM sales
GROUP BY customer_id;
SQL2(Incorrect):
SELECT customer_id, AVG(amount) as total_sales-- Incorrect aggregate function
FROM sales
GROUP BY customer_id;
C.2.4. MISUSE OF DISTINCT AND GROUP BY
Incorrect use of DISTINCT and GROUP BY clauses leading to incorrect results.
Query: Get the unique list of product categories.
SQL1(Correct):
SELECT DISTINCT category FROM products;
SQL2(Incorrect):
SELECT category FROM products GROUP BY category, price;-- Incorrect grouping,
→ changes semantics
C.2.5. INCORRECT SUBQUERIES
Using subqueries incorrectly that lead to incorrect results.
Query: List the names of customers who have placed an order.
SQL1(Correct):
SELECT customer_name
FROM customers
WHERE customer_id IN (SELECT customer_id FROM orders);
SQL2(Incorrect- assuming subquery might return multiple rows for ’=’):
SELECT customer_name
FROM customers
WHERE customer_id = (SELECT customer_id FROM orders);-- Incorrect if subquery
→ returns >1 row
C.2.6. INCORRECT FILTERING WITH AND/OR
Misusing AND/OR in WHERE clauses that lead to incorrect results.
Query: Retrieve all products that are in category ’Electronics’ AND cost more than $100.
SQL1(Correct):
SELECT * FROM products WHERE category = ’Electronics’ AND price > 100;
SQL2(Incorrect):
SELECT * FROM products WHERE category = ’Electronics’ OR price > 100;-- Incorrect
→ logical operator
18
LLM-Based Equivalence Evaluation for Text-to-SQL
C.2.7. INCORRECT ORDER BY CLAUSES
Using incorrect ORDER BY clauses that lead to incorrect sorting.
Query: List all products ordered by price from highest to lowest.
SQL1:
SELECT * FROM products ORDER BY price DESC;
SQL2(Incorrect):
SELECT * FROM products ORDER BY price ASC;-- Incorrect sort order
C.2.8. MISUSE OF FUNCTIONS
Using incorrect functions or misusing functions that lead to incorrect results.
Query: Find the length of each product name. (Assuming LENGTH and CHAR LENGTH might differ for some charsetsDBs)
SQL1(Correct for byte length, or char length if DB treats them same):
SELECT product_name, LENGTH(product_name) as name_length
FROM products;
SQL2 (Potentially Incorrect if expecting byte length and CHA LENGTH gives char count for multi-byte chars):
SELECT product\_name, CHAR\_LENGTH(product_name) as name_length
FROM products;
D. Prompt Examples
This section provides examples of prompts used to guide the LLM in assessing SQL equivalence.
D.1. Basic Prompt example for Equivalence Assessment
Basic Prompt Template
You are a database analyst and an SQL expert. Your task is to determine if two given
SQL queries are semantically equivalent. The queries are intended for [Application
name].
Please follow the following rules:
[rules]
and below are some examples:
[examples]
NL query: [NL query]
Query 1: [SQL1]
Query 2: [SQL2]
Please think step by step, and provide your reasoning before giving the final answer.
Output your answer in the following json format:
{
}
"reasoning": "Your reasoning here",
"equivalence": "equivalent" or "not equivalent"
19
LLM-BasedEquivalenceEvaluationforText-to-SQL
D.2.ImprovedPromptexampleforEquivalenceAssessment
ImprovedPromptTemplate
Task: DetermineiftwogivenSQLqueriesaresemanticallyequivalent. Thequeries
areintended for[Applicationname].
Thecriteria ofequivalenceoftwoSQLqueriesaredefinedasfollows: [detailed
criteriaofequivalence]
andthecriteriaoftheassessmentare: [detailedcriteriaofgrading]
Pleasefollowthefollowingrules:
[rules]
andbelowaresomeexamples:
[exampleswithChain-of-Thought] NLquery: [NLquery]
Query1: [SQL1]
Query2: [SQL2]
[OptionalSchemaInformationHere]
[OptionalQueryExecutionResultsHere]
Pleasethink stepbystep,andprovideyourreasoningbeforegivingthefinalanswer.
Outputyouranswerinthefollowingjsonformat:
{
"reasoning":"Yourreasoninghere",
"overallaccessment":"equivalent"/"minordifference"/"significant
→difference"/"notequivalent"/"undermined"
}
D.3.PromptforMiniature&MullStrategy
Miniature&MullPromptTemplate(Zhaoetal.,2024)
/* Giventhe followingtwoSQLqueriesQ1andQ2 */
SQL1:[SQL1]SQL2:[SQL2]
/* Andthefollowingdatabaseschema: */
[schema]
/* AreQ1andQ2semanticallyequivalent?
1. TryoneexampledatabaseandchecktheoutputtableofQ1andQ2. Databaseis
case-sensitivewhencomparingstring values.
2. Ifthe outputsareidentical,adjustthedatabasetoseehowoutputtablesofQ1
andQ2change.
3. Afterevaluatingwhetherthere existsadatabasesuchQ1andQ2outputdifferent
tables,writeyouranswerusingformatdecision="equivalent"ordecision=
"inequivalent". */
/* Let’sthinkstepbystep. */
1. Considerthefollowingexample databaseinstance,whichisstringvalue
case-sensitive,andexecuteQ1and Q2.
D.4.CombinedPromptexample:DetailedAssessmentwithMiniature&MullReasoning
CombinedPrompt:DetailedAssessmentwithMiniature&Mull
Task: DetermineiftwogivenSQLqueriesaresemanticallyequivalent. Thequeries
areintended for[Applicationname].
Thecriteria ofequivalenceoftwoSQLqueriesaredefinedasfollows: [detailed
criteriaofequivalence]
Andthecriteriaoftheassessmentare: [detailedcriteriaofgrading]
Pleasefollowthefollowingrules: [rules]
Andbelowaresomeexamples: [exampleswithChain-of-Thought,potentiallyshowing
M&Mstylereasoning]
NLquery: [NLquery]
Query1(Q1): [SQL1]
Query2(Q2): [SQL2]
20
LLM-Based Equivalence Evaluation for Text-to-SQL
Database Schema: [schema]
[Optional: Other Context or Query Execution Results if not using M&M exclusively for
execution simulation]
To determine semantic equivalence, please adopt the following "Miniature & Mull"
thinking process: 1. Try one example database instance based on the provided schema.
Execute Q1 and Q2 on this database. Remember the database is case-sensitive when
comparing string values. 2. If the outputs of Q1 and Q2 are identical on this first
instance, adjust the database (e.g., add/remove/modify rows or values) to create
a new instance. Re-execute Q1 and Q2 and observe how their output tables change.
3. Repeat step 2 if necessary, trying to find a database instance where Q1 and Q2
produce different output tables.
After thoroughly applying this thinking process, please provide your reasoning and
final assessment. Output your answer in the following JSON format:
{
}
"reasoning": "Your step-by-step reasoning, including the database instances
→ considered and the outputs of Q1 and Q2 on them, and how this led to your
→ conclusion.",
"overall_assessment": "equivalent" / "minor_difference" / "significant_difference"
→ / "not_equivalent" / "undetermined"
E. Evaluation Algorithms
21
LLM-Based Equivalence Evaluation for Text-to-SQL
Algorithm 1 SQL Equivalence Evaluation Pipeline (Basic)
1: Input: SQL Query Pair (Q1,Q2), Database Schema S (optional), Execution Results R (optional)
2: Output: Equivalence Judgment (Equivalent, Not Equivalent, Unstable)
3: {Step 1: Preprocessing}
4: Q′
1 ← Preprocess(Q1) {Standardize formatting, e.g., date/time, filters}
5: Q′
2 ← Preprocess(Q2)
6: {Step 2: String-based Matching}
7: if ExactMatch(Q′
1,Q′
2) then
8:
return Equivalent
9: end if
10: if ExactSetMatch(Q′
1,Q′
2,S) then
11:
return Equivalent
12: end if{Note: If string-based methods determine clear inequivalence, could return Not Equivalent here, or proceed to
LLMfor deeper analysis/explanation.}
13: {Step 3: LLM-based Evaluation (Standard Prompting)}
14: Initialize judgments ← []
15: Set default runs ← 3, max runs ← 5
16: Set current runs ← default runs
17: for i = 1 to current runs do
18:
19:
20:
prompt ← ConstructPrompt(Q′
1,Q′
2,S,R) {See Appendix D for basic prompt}
judgmenti ← LLM Query(prompt,GPT-4 model)
Add judgmenti to judgments
21: end for
22: if all judgment ∈ judgments are identical then
23:
25:
return judgments[0]
24: else
{Judgments vary, result is unstable}
26:
27:
28:
29:
30:
31:
32:
33:
34:
35:
36:
37:
38:
39:
40:
41:
if current runs < max runs then
{Optional: Increase runs for unstable cases}
for i = current runs+1 to max runs do
prompt ← ConstructPrompt(Q′
1,Q′
2,S,R)
judgmenti ← LLM Query(prompt,GPT-4 model)
Add judgmenti to judgments
end for
final judgment ← MajorityVote(judgments)
if final judgment is conclusive then
return final judgment
else
return Unstable {Even after more runs}
end if
else
return Unstable
end if
42: end if
22
LLM-Based Equivalence Evaluation for Text-to-SQL
Algorithm 2 Improved SQL Equivalence Evaluation Pipeline with Query Rewrite and Miniature & Mull Strategy
1: Input: SQL Query Pair (Q1,Q2), Database Schema S (optional)
2: Output: Equivalence Judgment (Equivalent, Not Equivalent, Unstable)
3: {Step 1: Preprocessing}
4: Q1p ← Preprocess(Q1) {Standardize formatting}
5: Q2p ← Preprocess(Q2)
6: {Step 2: Query Rewrite for Subqueries}
7: Q1r ← RewriteSubqueriesToJoins(Q1p) {e.g., to LEFT JOIN}
8: Q2r ← RewriteSubqueriesToJoins(Q2p)
9: {Step 3: String-based Matching (on potentially rewritten queries)}
10: if ExactMatch(Q1r,Q2r) then
11:
return Equivalent
12: end if
13: if ExactSetMatch(Q1r,Q2r,S) then
14:
return Equivalent
15: end if
16: {Step 4: LLM-based Evaluation with Miniature & Mull}
17: Initialize judgments ← []
18: Set default runs ← 3, max runs ← 5
19: Set current runs ← default runs
20: for i = 1 to current runs do
21:
22:
23:
prompt ← ConstructMiniatureAndMullPrompt(Q1r,Q2r,S) {Instructs LLM to create DB, execute, modify DB,
re-execute, compare}
judgmenti ← LLM Query(prompt,GPT-4 model)
Add judgmenti to judgments
24: end for
25: if all judgment ∈ judgments are identical then
26:
28:
return judgments[0]
27: else
{Judgments vary, result is unstable}
29:
30:
31:
32:
33:
34:
35:
36:
37:
38:
39:
40:
41:
42:
43:
44:
if current runs < max runs then
{Optional: Increase runs for unstable cases}
for i = current runs+1 to max runs do
prompt ← ConstructMiniatureAndMullPrompt(Q1r,Q2r,S)
judgmenti ← LLM Query(prompt,GPT-4 model)
Add judgmenti to judgments
end for
final judgment ← MajorityVote(judgments)
if final judgment is conclusive then
return final judgment
else
return Unstable {Even after more runs}
end if
else
return Unstable
end if
45: end if