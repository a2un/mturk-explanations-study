docker build -t mturk-explanations-ui ./ -f Dockerfile.streamlit

docker stop mturk-explanations-ui-container
docker rm mturk-explanations-ui-container

docker run --privileged=true -d --name mturk-explanations-ui-container -p 14358:14358 -v $(pwd)/data:/mturk-explanation-study/data mturk-explanations-ui
