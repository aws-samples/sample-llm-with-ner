import boto3
import logging
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.nlp.stemmers import Stemmer
from sumy.summarizers.luhn import LuhnSummarizer
from sumy.utils import get_stop_words
from sumy.summarizers.text_rank import TextRankSummarizer

import os
import json
import threading

s3 = boto3.client('s3')
nltk_data_path = os.path.join(os.getcwd(), 'nltk_data')

EXTRACTS_BUCKET = os.environ['EXTRACTS_BUCKET']
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']

SENTENCES_COUNT = 10
logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info(f"nltk_data_path: {nltk_data_path}")
logger.info(f"NLTK files: {os.listdir(nltk_data_path)}")


def init_nltk():
    try:
        nltk.data.path.append(nltk_data_path)
        nltk.data.find('tokenizers/punkt')
        logger.info("NLTK data found successfully")
    except LookupError as e:
        logger.error(f"NLTK data not found: {str(e)}")
        raise


def read_file_from_s3(bucket, key):
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj['Body'].read().decode('utf-8', errors='ignore')


def summarize_text(text, SENTENCES_COUNT=SENTENCES_COUNT):
    stemmer = Stemmer("english")
    parser = PlaintextParser.from_string(text, Tokenizer("english"))

    summarizer = TextRankSummarizer(stemmer)
    summarizer.stop_words = get_stop_words("english")

    summary = summarizer(parser.document, SENTENCES_COUNT)
    text_summary = ""
    for sentence in summary:
        text_summary += str(sentence)

    return text_summary


def luhn_summarization(text, SENTENCES_COUNT=SENTENCES_COUNT):
    print("Switching to Luhn summarization for time optimization.")
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LuhnSummarizer()
    summary = summarizer(parser.document, SENTENCES_COUNT)
    summary_sentences = [str(sentence) for sentence in summary]
    return " ".join(summary_sentences)


def ext_summary_with_timeout(text, SENTENCES_COUNT=SENTENCES_COUNT, timeout=600):
    result = []

    def summarization_task():
        result.append(summarize_text(text, SENTENCES_COUNT=SENTENCES_COUNT))

    thread = threading.Thread(target=summarization_task)
    thread.start()

    thread.join(timeout=timeout)

    if thread.is_alive():
        print("Time exceeded, switching to Luhn summarization.")
        thread.join()  # Clean up thread
        return luhn_summarization(text, SENTENCES_COUNT=SENTENCES_COUNT)
    else:
        return result[0] if result else "No summary generated."


def lambda_handler(event, context):
    logger.info(f"event: {event}")

    init_nltk()

    extracts_file_name = json.loads(event.get('body')).get('uid')
    logger.info(f"extracts_file_name: {extracts_file_name}")
    extractive_summary_file_name = extracts_file_name.replace("_extracted_text.txt", ".txt")

    text = read_file_from_s3(EXTRACTS_BUCKET, extracts_file_name)
    text_summary = ext_summary_with_timeout(text, SENTENCES_COUNT=SENTENCES_COUNT)

    s3.put_object(
        Body=text_summary,
        Bucket=OUTPUT_BUCKET,
        Key=extractive_summary_file_name
    )

    return {
        'statusCode': 200,
        'uid': extractive_summary_file_name,
        "MessageDetails": event.get("MessageDetails")
    }
