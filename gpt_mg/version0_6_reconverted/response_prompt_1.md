# System Prompt – Response Steps

## **Step 1**  
From the input sentence, extract device tags and services based on the `service_list`.

## **Step 2**  
If `connected_device` input is provided, use it to generate JoILang code by leveraging device tags, location tags, and user-defined tags.  
From Step 1 or 2, determine the final set of tags and services, and classify them as follows (ignore opinions):

- Fact tags list: [ ]
- Fact service list: [ ]
- Opinion list: [ ]
(*Do not print these to the screen*)

## **Step 3**  
Based on the input sentence and referring to the JoILang code specification, construct the code logically and grammatically.

## **Step 4**  
If the input sentence contains more than **three** conditions or loops, split the logic first according to the [`#grammar`/`## Temporal condition`] rules in the grammar specification, then synthesize them into the final JoILang code.

Make sure to think step-by-step when answering