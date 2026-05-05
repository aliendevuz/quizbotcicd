from src.app import handle_lambda_request


def lambda_handler(event, context):
	return handle_lambda_request(event, context)
