"""
Script to perform batch scoring.
"""
import os
import pandas_gbq
import pickle
import time
import lightgbm as lgb
from utils.constants import FEATURE_COLS
from utils.preprocess import generate_features
from pyspark.sql import SparkSession

OUTPUT_MODEL_NAME = os.getenv('OUTPUT_MODEL_NAME')
DEST_BIGQUERY_PROJECT = os.getenv("RAW_BIGQUERY_PROJECT")
DEST_BIGQUERY_DATASET = os.getenv("RAW_BIGQUERY_DATASET")
DEST_SUBSCRIBER_SCORE_TABLE = os.getenv("DEST_SUBSCRIBER_SCORE_TABLE")


if __name__ == '__main__':
    with SparkSession.builder.appName("BatchScoring").getOrCreate() as spark:
        spark.sparkContext.setLogLevel("FATAL")

        start = time.time()
        print("\tLoading active subscribers")
        subscriber_df = generate_features(spark)
        subscriber_pandasdf = (
            subscriber_df
            .filter(subscriber_df["Churn"] == 0)
            .drop("Churn")
            .toPandas()
        )
        print("\tTime taken = {:.2f} min".format((time.time() - start) / 60))
        print("\tNumber of active subscribers = {}".format(subscriber_pandasdf.shape[0]))

    print("\tLoading model")
    with open("/artefact/" + OUTPUT_MODEL_NAME, "rb") as model_file:
        gbm = pickle.load(model_file)

    print("\tScoring")
    subscriber_pandasdf["Prob"] = gbm.predict(subscriber_pandasdf[FEATURE_COLS])

    start = time.time()
    print("\tSaving scores to BigQuery")
    subscriber_pandasdf[["User_id", "Prob"]].to_gbq(
        f"{DEST_BIGQUERY_DATASET}.{DEST_SUBSCRIBER_SCORE_TABLE}",
        project_id=DEST_BIGQUERY_PROJECT,
        if_exists="replace",
    )
    print("\tTime taken = {:.2f} min".format((time.time() - start) / 60))