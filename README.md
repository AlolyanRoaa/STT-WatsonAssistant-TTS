# STT - Watson Assistant - TTS

Python application that uses a IBM Watson services speech to text, Watson Assistant, and text to speech. This project is completely dependent on the previous repository ([STT-TTS-IBMWatson](https://github.com/AlolyanRoaa/STT-TTS-IBMWatson)), it is an updated version of the project, that merge Watson Assistant with STT-TTS application to get a response from the assistant.

so, please [click here](https://github.com/AlolyanRoaa/STT-TTS-IBMWatson) to go to the repository.


you must have been created a chatbot for the project before ahead and have assigned this skill to your assistant, for an Arabic tutorial check [this repository](https://github.com/shaimadotcom/ibm_watson_assistant).


Note: PyCharm IDE was used while implementing this project.

## Outline

- Application workflow
- Updates needed on the previous version
- Demo


## Application Workflow


![workflow](https://github.com/AlolyanRoaa/STT-WatsonAssistant-TTS/blob/main/images/workflow.png "Workflow of STT-Watson Assistant-TTS application")


User will start speaking to the system, the system will catch what the user says and change it to text form by using the Speech to Text service provided by IBM Watson, ​Then that Text will be an input to the chatbot that we created previously and assigned our assistant with it.


then the response message from the chatbot will go as text input to the Text to Speech service, you will get an audio mp3 file as an output, now all left to the system is to play this mp3 file.



## Updates Needed on The Previous Version

all update was done inside *on_close()* function, we started by getting the assistant authentication

```bash
    # ... get assistant authentication
    authenticator = IAMAuthenticator('{apikey}')
    assistant = AssistantV2(
        version='2021-06-14',
        authenticator=authenticator
    )
    assistant.set_service_url('https://api.us-south.assistant.watson.cloud.ibm.com')
```

now create a session and convert a python object to a json string.


```bash 
    # ... create session
    session = assistant.create_session(
        assistant_id='{assistant_id}'
    ).get_result()
    
    # ... converts a obj to a json string
    session_js = json.dumps(session, indent=2)
    
    # ... returns obj dictionary
    session_dict = json.loads(session_js)
    session_id = session_dict['session_id']
```


then get the response from the assistant and convert it and store it to MassageText variable.


```bash 
     response = assistant.message(
        "{assistant_id}",
        session_id,
        input={'text': transcript},
    ).get_result()

    message_js = json.dumps(response, indent=2)
    message_dict = json.loads(message_js)
    MassageText = message_dict["output"]["generic"][0]["text"]
```


now save the response to text file so we can apply TTS on it.


```bash
    # now write the final into output.txt file
    with codecs.open('output.txt', 'w', encoding='utf-8') as f:
        json.dump(MassageText, f, ensure_ascii = False)
```


## Demo


<img src="https://github.com/AlolyanRoaa/STT-WatsonAssistant-TTS/blob/main/images/DemoPic.PNG" width="500">


https://user-images.githubusercontent.com/85321139/128555782-f2ef7cbc-7153-4cc1-a336-fa79b962773e.mp4






