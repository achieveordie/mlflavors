import json

import mlflow
import pandas as pd
from sktime.datasets import load_longley
from sktime.forecasting.model_selection import temporal_train_test_split
from sktime.forecasting.naive import NaiveForecaster
from sktime.performance_metrics.forecasting import (
    mean_absolute_error,
    mean_absolute_percentage_error,
)

import mlflow_flavors

ARTIFACT_PATH = "model"

with mlflow.start_run() as run:
    y, X = load_longley()
    y_train, y_test, X_train, X_test = temporal_train_test_split(y, X)

    forecaster = NaiveForecaster()
    forecaster.fit(
        y_train,
        X=X_train,
        fh=[1, 2, 3, 4],
    )

    # Extract parameters
    parameters = forecaster.get_params()

    # Evaluate model
    y_pred = forecaster.predict(X=X_test)
    metrics = {
        "mae": mean_absolute_error(y_test, y_pred),
        "mape": mean_absolute_percentage_error(y_test, y_pred),
    }

    print(f"Parameters: \n{json.dumps(parameters, indent=2)}")
    print(f"Metrics: \n{json.dumps(metrics, indent=2)}")

    # Log parameters and metrics
    mlflow.log_params(parameters)
    mlflow.log_metrics(metrics)

    # Log model using custom model mlflow_flavors with pickle serialization (default).
    mlflow_flavors.sktime.log_model(
        sktime_model=forecaster,
        artifact_path=ARTIFACT_PATH,
        serialization_format="pickle",
    )
    model_uri = mlflow.get_artifact_uri(ARTIFACT_PATH)

# Load model in native sktime flavor and pyfunc flavor
loaded_model = mlflow_flavors.sktime.load_model(model_uri=model_uri)
loaded_pyfunc = mlflow_flavors.sktime.pyfunc.load_model(model_uri=model_uri)

# Convert test data to 2D numpy array so it can be passed to pyfunc predict using
# a single-row Pandas DataFrame configuration argument
X_test_array = X_test.to_numpy()

# Create configuration DataFrame for interval forecast with nominal coverage
# value [0.9,0.95], future forecast horizon of 3 periods, and exogenous regressor.
predict_conf = pd.DataFrame(
    [
        {
            "fh": [1, 2, 3],
            "predict_method": "predict_interval",
            "coverage": [0.9, 0.95],
            "X": X_test_array,
        }
    ]
)

# Generate interval forecasts with native sktime flavor and pyfunc flavor
print(
    f"\nNative sktime 'predict_interval':\n$ \
    {loaded_model.predict_interval(fh=[1, 2, 3], X=X_test, coverage=[0.9, 0.95])}"
)
print(f"\nPyfunc 'predict_interval':\n${loaded_pyfunc.predict(predict_conf)}")

# Print the run id wich is used for serving the model to a local REST API endpoint
# in the request_prediction.py module
print(f"\nMLflow run id:\n{run.info.run_id}")
