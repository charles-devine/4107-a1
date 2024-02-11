import math
import os
import json
import nltk
nltk.download('punkt')
import time
import numpy as np
import ssl
import re  # Import the 're' module for regular expressions
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
import xml.etree.ElementTree as ET
from numpy.linalg import norm

start_time = time.time()

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

custom_stopwords_file = 'stopwords.txt'
collection_folder = 'coll'
output_tokens_json_file = 'tokens.json'
file_path = 'test_queries.txt'

# Load custom stopwords
with open(custom_stopwords_file, 'r') as f:
    custom_stopwords = set(f.read().splitlines())

# Initialize NLTK's PorterStemmer
porter_stemmer = PorterStemmer()

number_of_docs = 79923

##################################
def preprocess_text(text):
    tokens = word_tokenize(text)
    tokens = [re.sub(r'[^a-zA-Z]', '', token) for token in tokens]
    tokens = [token.lower() for token in tokens]
    tokens = [token for token in tokens if token not in custom_stopwords]
    tokens = [porter_stemmer.stem(token) for token in tokens]
    return tokens

def index_topic_tokens(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    topics = re.findall(r'<top>(.*?)</top>', content, re.DOTALL)
    indexed_tokens = {}

    for topic in topics:
        num = re.search(r'<num>\s*(\d+)\s*', topic)
        title = re.search(r'<title>\s*(.*?)\s*\n', topic)
        desc = re.search(r'<desc>\s*.*?\s*(.*?)\s*\n', topic, re.DOTALL)
        if num and title and desc:
            num = num.group(1).strip()
            title_text = title.group(1).strip()
            desc_text = desc.group(1).strip()
            # Preprocess title and description
            title_tokens = preprocess_text(title_text)
            desc_tokens = preprocess_text(desc_text)

            # Token frequency indexing
            indexed_tokens[num] = {
                'title': {token: title_tokens.count(token) for token in set(title_tokens)},
                'desc': {token: desc_tokens.count(token) for token in set(desc_tokens)}
            }        
    return indexed_tokens

# Define a function to clean XML content using regex
def clean_xml_content(xml_content):
    # Define a regular expression pattern to match lines not encapsulated by <DOCNO> and <TEXT> tags
    pattern = r'<(?!DOCNO|TEXT)[^>]*>.*?</[^>]*>\n?'

    cleaned_xml_content = re.sub(pattern, '', xml_content)
    return cleaned_xml_content

def preprocess_document(document):
    # Tokenize the document
    tokens = word_tokenize(document)
    tokens = [re.sub(r'[^a-zA-Z]', '', token) for token in tokens]
    tokens = [token.lower() for token in tokens]
    tokens = [token for token in tokens if token not in custom_stopwords]
    tokens = [porter_stemmer.stem(token) for token in tokens]
    
    return tokens

def preprocess_query(query):
    tokens = word_tokenize(query)
    tokens = [token.lower() for token in tokens if token.isalpha()]
    tokens = [token for token in tokens if token not in custom_stopwords]
    tokens = [porter_stemmer.stem(token) for token in tokens]
    
    return tokens

def preprocess_documents(folder):
    preprocessed_docs = {}
    unique_tokens = set()  # Set to keep track of unique tokens
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if os.path.isfile(filepath):
            with open(filepath, 'r', encoding='utf-8') as file:
                document_content = file.read()
                # Extract <DOCNO> tags using regex
                doc_no_matches = re.findall(r'<DOCNO>(.*?)<\/DOCNO>', document_content, re.DOTALL)
                for doc_no in doc_no_matches:
                    # Find all occurrences of <TEXT> tags after the current <DOCNO>
                    text_matches = re.findall(r'<DOCNO>{}</DOCNO>(.*?)<\/TEXT>'.format(re.escape(doc_no)), document_content, re.DOTALL)
                    tokens = []
                    for text in text_matches:
                        # Preprocess each text and update tokens list
                        tokens.extend(preprocess_document(clean_xml_content(text)))
                    tokens = list(tokens)  # Remove duplicates
                    preprocessed_docs[doc_no] = tokens
                    unique_tokens.update(tokens)
    return preprocessed_docs, unique_tokens

def index_tokens(preprocessed_docs):
    tokens_dict = {}
    for doc_no, tokens in preprocessed_docs.items():
        for token in tokens:
            if token not in tokens_dict:
                tokens_dict[token] = {doc_no: 1}
            else:
                if doc_no in tokens_dict[token]:
                    tokens_dict[token][doc_no] += 1
                else:
                    tokens_dict[token][doc_no] = 1
    for token, doc_counts in tokens_dict.items():
        if token == "text":
            for doc_no, count in list(doc_counts.items()):
                if count == 1:
                    del tokens_dict[token][doc_no]  # Remove the token count if it is 1
                else:
                    tokens_dict[token][doc_no] -= 1  # Decrement the count by 1 if more than 1
    tokens_dict.pop("", None)
    return tokens_dict
def cleanQuery(query):
    seen = set()
    unique_query = [x for x in query if not (x in seen or seen.add(x))]
    queryCounts = [query.count(word) for word in unique_query]
    return unique_query, queryCounts

def idf_calculation(query): 
    arr = [] 
    query, count = cleanQuery(query)
    for token in query: 
        if token in tokens_dict: 
            arr.append(math.log2(number_of_docs/len(tokens_dict[token])))        
    return arr

def tf_calculation(query): 
    arr = []
    tmp = []
    res = []
    fin = []
    fullQuery = query
    query, queryCounts = cleanQuery(fullQuery)
    tmp.append("query")
    for i in range(len(queryCounts)):
        if query[i] in tokens_dict:
            tmp.append(queryCounts[i])
    res.append(tmp)
    tmp = []
    # Calculate tf query 
    for token in query: 
        if token in tokens_dict:
            arr = list(tokens_dict[token].keys())
            for i in range(len(arr)):
                if arr[i] not in tmp:
                    tmp.append(arr[i])
                    fin.append(arr[i])
                    for j in query:
                        if j in tokens_dict:
                            if tokens_dict[j].get(arr[i]) != None:
                                fin.append(tokens_dict[j].get(arr[i]))
                            else: 
                                fin.append(int(0))
                    res.append(fin)
                    fin = []
           
    for i in range(len(res)):
        maximum = max(res[i][1:])
        for j in range(1,len(res[i])):
            res[i][j] = res[i][j]/maximum
    return res

def tf_idf_score(query): 
    tf = tf_calculation(query)
    idf = idf_calculation(query)
    tf_idf = []
    for i in range(len(tf)):
        tempList = [tf[i][0]]
        for j in range(1,len(tf[i])):
            tempList.append(tf[i][j]*idf[j-1])
        tf_idf.append(tempList)
    return tf_idf

def cosine_calculator(query): 
    tf_idf = tf_idf_score(query)
    qtf_idf = tf_idf[0]
    cosineValue = []
    for i in range(1,len(tf_idf)):
        val = []
        val.append(tf_idf[i][0])
        q = np.array(qtf_idf[1:])
        doc = np.array(tf_idf[i][1:])
        dotproduct = np.dot(q,doc)/(norm(q)*norm(doc))
        val.append(dotproduct)
        cosineValue.append(val)
    cosineValue = sorted(cosineValue, key = lambda x: x[1], reverse=True)
    return cosineValue

def getQueryTitle(runName):
    result = ""
    qnum = 1
    for key, value in indexed_tokens.items(): 
        query = ""
        title_array = []
        title_count = []
        title = value.get('title', {})
        for key, value in title.items(): 
            title_array.append(key); 
            title_count.append(value); 
        for i in range(len(title_array)):
            for j in range(title_count[i]):
                query += title_array[i] + " "  
        cosine = cosine_calculator(preprocess_document(query))
        count = 1
        for j in cosine:
            if count <= 1000:
                data = ""
                data = str(qnum) + " Q0" + j[0]  + str(count) + " " + str(j[1]) + " " + runName + "\n"    
                count += 1
                result += data
            else: 
                break
        qnum += 1    
    with open('Result.txt', 'w') as file: 
        file.write(result); 

def getQueryTitleDesc(runName): 
    result = ""
    qnum = 1
    for key, value in indexed_tokens.items(): 
        query = ""
        title_array = []
        title_count = []
        title = value.get('title', {})
        for keyt, valuet in title.items(): 
            title_array.append(keyt)
            title_count.append(valuet)
        desc = value.get('desc', {})
        for keyd, valued in desc.items():
            title_array.append(keyd) 
            title_count.append(valued)
        for i in range(len(title_array)):
            for j in range(title_count[i]):
                query += title_array[i] + " "  
        cosine = cosine_calculator(preprocess_document(query))
        count = 1
        for j in cosine:
            if count <= 1000:
                data = ""
                data = str(qnum) + " Q0" + j[0]  + str(count) + " " + str(j[1]) + " " + runName + "\n"    
                count += 1
                result += data
            else: 
                break
        qnum += 1    
    with open('Result.txt', 'w') as file: 
        file.write(result); 
##################################
# Index the tokens
indexed_tokens = index_topic_tokens(file_path)
# Save to JSON file
output_json_file = 'indexed_topics.json'
with open(output_json_file, 'w', encoding='utf-8') as jsonfile:
    json.dump(indexed_tokens, jsonfile, indent=4)
# Call preprocess_documents to preprocess the documents
preprocessed_docs, unique_tokens = preprocess_documents(collection_folder)

# Call index_tokens to index the tokens
tokens_dict = index_tokens(preprocessed_docs)

# Add total unique token count at the end
tokens_dict["total_unique_tokens"] = len(unique_tokens)

# Write the tokens dictionary to a JSON file
with open(output_tokens_json_file, 'w', encoding='utf-8') as jsonfile:
    json.dump(tokens_dict, jsonfile, indent=4)

# Record the end time after writing the JSON file
end_time = time.time()


getQueryTitleDesc("Run 1")
# Calculate the elapsed time
elapsed_time = end_time - start_time
print(f"Time taken to load and process JSON file: {elapsed_time} seconds")

