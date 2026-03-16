# High level walk through
Data:
- `bug_data_training.json` - used to build model
- `bug_data.json` - run through to see how it works
- `product_context.json`
- `defect_criteria.json`


1. `run_pipeline.py` - runs each of the following scripts:
    1. `complaint_triage.py`
        - outputs: `call_1_defect_classification_results.json` 
    2. `probability.py`
        - outputs: `call_2_probability_results.json`
    3. `severity.py`
        - outputs: `call_3_severity_results.json`
    4. `final_scoring.py`
        - makes all the calls, calculates risk based on matrix, assembles final report (of complaints, CAPAs and defects)
    4. `defect_criteria.json`


- `run_pipeline.py`
    - ensures all input data files already exist (and have data)
    - ensures api key is set
    - **Article note - best time to catch a bug is before sending to an LLM - need to be very percise with checking all your data is in order before kicking off an LLM pipeline with clear failure messages**

- `complaint_triage.py`
    - Overvie - pulls in bug_data - **article note - this would likely be more like coming in from your ticketing system api**
    - 1. clean and format your json object corretly - **article note - want to only send the exact info you need to send to your llm, be percise**
    - 2. calls `defect_criteria.json` in prompt which has:
        - explination of SOP
        - **Article note/limitation - there's probably more determinism I can add to here, it's a balance between being as deterministic as possible but also getting something working.  I would think in the real world you end up get something up and running, then reduce to more deteminism overtime, cause the draw back of having 100% everything possible in this example be deterministic is that you may make the ai workflow flakey**
        - description of product, components, features, defect criteria, risk matrix guidance 
    - 3. calls `product_context.json` -
        - list of `user_needs` and `product_requirements` 
            - (and clinical_safety_criteria which is unused)
        - **article note/limitation - this would likely need to be refactored in a real product, just have like 15 reqs in this example instead of 100s, in real case, may be hitting your eQMS api and have some clever structuring to preprocess the bug to look for the feature category it likely sits in then review those requirements**
    - 4. LLM prompt:
        - determine if in the released product (based on bug input data) - *this could be determinstic*
        - Review bug and review user needs and product requirements to determine if it directly violates one of those
        - both criteria need to be met to = defect 
    - 5. response structure
        - gives clear structure for the llm to respond in 
        - **article note - in your prompt you want to force the llm to respond in a certain way, in this case a specific json format which allows you to then utilize that information in a determinstic way in future calls, for example, here I have `"criterion_2_failed_requirements": ["PR-XXX", "PR-YYY"] or []"`, this way I clearly get back which requirement the llm thinks it fails, so I can easily review.  This step alone is extremly valuable in the complaint triage/bug resolution pipeline in SaMD**
    - 6. Loop through bugs and run llm call on each
        - **article note - each llm call should be as targeted as possible, here each script will call the llm 1 time per each bug, this is a much more effective strategy than trying to give the llm 10 bugs at once and having it do all of them in a session - higher chance of halucination and/or just missing some of the input bugs**
    - 7. Output json file that will be input to next script
        - **article note - each step of your process should output a very clear deliverable that then is used as input to the next step, here I'm outputing into a json format which allows me to specify all fields of the deliverable vs trying to just output a paragraph of text which I would then need to wrangle on the next llm call**
- `probability.py`
    - Overview - based on inital triage output, assesses the bug's probability
    - 1. Pull in output of last llm call
        - **article note/limitation - error management crucial, and having robust infrastrucuture to stop llm calls from happening if you have some error in your data - think the first llm call fails, or is insufficent, all the steps moving forward will be compromised.  This is a big issue with AI, if you just let it run wild, it can cost a lot and give you a lot of nothing useful**
    - 2. LLM call - Probability prompt
        - give it the Probablity scale - and explain what each score means
        - **article note - in this toy example, I would say the assessments are useful, but mostly just guesses.  This could get incredibly more powerful if you had a dataset of past bugs and the user impact scope of those bugs connected to your code base.  Again, more clear context the better for the llm to function well**
        - Give it 'Factors to consider" - so essentially right now it works through the 'factors to consider' adn the dedetermines probability based on the scale.  Not a bad way, but more context would be infiently better - like dataset of past bugs
    - 3. LLM Call - Bug data
        - We already loaded our output from our last llm call and structured the data for use in or prompt.  Now we add the data into each prompt (via loop), so we can pull in 1. data from output, 2. orginal data
        - **article note - need an id (here `bug_id`) to link your json objects, you don't want to be creating entirely new json records every time, so it's really: (data.json -> script 1 -> output 1.json) -> (data.json + output 1.json -> script 2 -> output 2.json) etc.  Again, reduce the space the llm has to play and get lost in**
- `severity.py`
    - Overview - assesses severity, largely similar approach as probabiltiy 
    - **article note - how we have this structured also allows for not adding unnecessary context to each llm call, so in SaMD severity assessment should be a distinct discussion from probability discussion, this set up allows for exactly that, severity llm call does not see the output of the probability script**
- `final_scoring.py`
    - Overview - pulls together the output of all the other calls and puts them together
    - this is a completely deterministic script, no LLM call
    - **article note - so, for review, we took input data (from our ticketing system), then structured a handful of llm calls to drill into each bug and make an assessment, each assessment outputed a data file that is strucuted cleanly, now we're combining those data files and outputting a severity + probabilty score per our sop, then putting together a final report and grouping by CAPA, medium and low risk.  This puts together a report that will first be reviewed by a human (complain manager) and then taken as an agenda for a complaint review meeting.  The report is simplified, but any question that arises as to how a specific bug's assessment was made can be looked up in the associated data files (via `bug_id`), as we had the llm write a summary of why it made each decision along the way.**
    - **article note - This is the real magic: step by step, outputs from each step to allow for humans to trace issues and see what's going on.**
- `run_pipeline.py`
    - Overview - simple script to execute the pipeline with good error handeling 







# Overall article notes/learnings
- for a fake app which is SaMD mental health called "mindBridge"
- I built this in python because I was still thinking 'python is the ai langauge' but it seems from further research this is not necessary today (unless you're doing actual ai engineering and not just calling prompts), remember: openclaw is built in typescript
- Note total token use per bug (which may be higher based on real world use case)
- note total number of llm calls per bug
- High level - 
    1. break problem down into each miniamlly discrete step
    2. script and llm call for each step
    3. Identify all the areas/pieces of information that you can reduce to determinism - both going into LLM as well as coming out of llm
    4. If you have multiple items, break each step down into atomic llm calls, so here we're looping through each bug for each call. 1 bug = 1 call per each step.  Don't be sending multiple units to a single llm call, confuses llm
- Stress importance of computational thinking over necessarily just 'coding', the future is going to be less wrestling with syntax, more thinking through how to put real world scenarios into processes possible for machines to execute - think of it like you have an employee that is excellent at following directions, but they have a tendency to go off the rails if they are not told exactly what to do at every step...but you only have to tell them once when you want to change a behavior
- 

# Limitations
- some of the data fields like 'in_released_product' rely in bug ticket set up which is still done manually in this example and prone to human error
- Add on - could include a route where you determine the feature the bug is in
- 




# TO DO
- final_scoring.py 
    - `calculate_risk` - change this to be based on acutal 5x5 model, bnot numerical
    - Review final report setup
    - will need to update `defect_criteria.json` - `risk_levels`
- bug_data/training.json
    - review to see if it makes sense
    - have this expected classification/probability/severity - that's weird right?
- `compalint_triage.py` make 'bug in the released product' deterministic bsed on bug input data
- Add 'failed user needs' to 'Defect to assess in `probabilty.py`











# Future considerations
- Clinical safety assessment - at woebot there was a Step where the complaint review committee would send some issues to clinicians based on safety categorization that was not covered by the general severity ability matrix - covering that in this process or at least pre-processing to flag clinical safety risks could be helpful
- 