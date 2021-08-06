#!/usr/bin/env python
#
# Copyright 2016 IBM
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import argparse
import base64
import configparser
import json
import threading
import time
import codecs

import pyaudio
import websocket
from websocket._abnf import ABNF
from ibm_watson import AssistantV2
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from playsound import playsound





CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5
FINALS = []
LAST = None


REGION_MAP = {
    'us-east': 'gateway-wdc.watsonplatform.net',
    'us-south': 'stream.watsonplatform.net',
    'eu-gb': 'stream.watsonplatform.net',
    'eu-de': 'stream-fra.watsonplatform.net',
    'au-syd': 'gateway-syd.watsonplatform.net',
    'jp-tok': 'gateway-syd.watsonplatform.net',
}


def read_audio(ws, timeout):
    """Read audio and sent it to the websocket port.

    This uses pyaudio to read from a device in chunks and send these
    over the websocket wire.

    """
    global RATE
    p = pyaudio.PyAudio()
    RATE = int(p.get_default_input_device_info()['defaultSampleRate'])
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* recording")
    rec = timeout or RECORD_SECONDS

    for i in range(0, int(RATE / CHUNK * rec)):
        data = stream.read(CHUNK)
        ws.send(data, ABNF.OPCODE_BINARY)

    stream.stop_stream()
    stream.close()

    print("* done recording")

    data = {"action": "stop"}
    ws.send(json.dumps(data).encode('utf8'))

    # ... which we need to wait for before we shutdown the websocket
    time.sleep(1)
    ws.close()

    # ... and kill the audio device
    p.terminate()


def on_message(self, msg):
    """Print whatever messages come in.

    While we are processing any non trivial stream of speech Watson
    will start chunking results into bits of transcripts that it
    considers "final", and start on a new stretch. It's not always
    clear why it does this. However, it means that as we are
    processing text, any time we see a final chunk, we need to save it
    off for later.
    """
    global LAST
    data = json.loads(msg)

    if "results" in data:
        if data["results"][0]["final"]:
            FINALS.append(data)
            LAST = None

        else:
            LAST = data
        # This prints out the current fragment that we are working on
        print(data['results'][0]['alternatives'][0]['transcript'])


def on_error(self, error):
    """Print any errors."""
    print(error)


def on_close(ws):
    """Upon close, print the complete and final transcript."""
    global LAST

    # ... result message
    global MassageText
    global transcript

    # ... get assistant authentication
    authenticator = IAMAuthenticator('hayEEhutsxHR1dGQoWa3A5v2dKNe7vPhNJpDhJ3AUDgL')
    assistant = AssistantV2(
        version='2021-06-14',
        authenticator=authenticator
    )
    assistant.set_service_url('https://api.us-south.assistant.watson.cloud.ibm.com')

    if LAST:
        FINALS.append(LAST)
    transcript = "".join([x['results'][0]['alternatives'][0]['transcript']
                          for x in FINALS])

    # ... create session
    session = assistant.create_session(
        assistant_id='4677e28f-5d7b-4134-b19d-ee0455e93ad9'
    ).get_result()
    # ... converts a obj to a json string.
    session_js = json.dumps(session, indent=2)
    # ... returns obj dictionary
    session_dict = json.loads(session_js)
    session_id = session_dict['session_id']

    response = assistant.message(
        "4677e28f-5d7b-4134-b19d-ee0455e93ad9",
        session_id,
        input={'text': transcript},
    ).get_result()

    message_js = json.dumps(response, indent=2)
    message_dict = json.loads(message_js)
    MassageText = message_dict["output"]["generic"][0]["text"]

    print(MassageText)
    # now write the final into output.txt file
    with codecs.open('output.txt', 'w', encoding='utf-8') as f:
        json.dump(MassageText, f, ensure_ascii = False)

    return transcript


def on_open(ws):
    """Triggered as soon a we have an active connection."""
    args = ws.args
    data = {
        "action": "start",
        # this means we get to send it straight raw sampling
        "content-type": "audio/l16;rate=%d" % RATE,
        "continuous": True,
        "interim_results": True,
        # "inactivity_timeout": 5, # in order to use this effectively
        # you need other tests to handle what happens if the socket is
        # closed by the server.
        "word_confidence": True,
        "timestamps": True,
        "max_alternatives": 3
    }

    # Send the initial control message which sets expectations for the
    # binary stream that follows:
    ws.send(json.dumps(data).encode('utf8'))
    # Spin off a dedicated thread where we are going to read and
    # stream out audio.
    threading.Thread(target=read_audio,
                     args=(ws, args.timeout)).start()


def get_url():
    config = configparser.RawConfigParser()
    config.read('speech.cfg')
    # See
    # https://console.bluemix.net/docs/services/speech-to-text/websockets.html#websockets
    # for details on which endpoints are for each region.
    region = config.get('auth', 'region')
    host = REGION_MAP[region]
    return ("wss://{}/speech-to-text/api/v1/recognize"
           "?model=en-US_BroadbandModel").format(host)


def get_auth():
    config = configparser.RawConfigParser()
    config.read('speech.cfg')
    apikey = config.get('auth', 'apikey')
    return ("apikey", apikey)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Transcribe Watson text in real time')
    parser.add_argument('-t', '--timeout', type=int, default=5)
    # parser.add_argument('-d', '--device')
    # parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()
    return args


def convert_to_voice():
    # the model of TTS
    key = 'z0eveTuFc0uQ5zzrjP4EUe5bNxLRMmZeCkGX-MnU2eRh'
    url = 'https://api.us-south.text-to-speech.watson.cloud.ibm.com/instances/9aa931bd-c308-436f-bd45-1dcd64bb0508'

    # Authenticate
    authenticator = IAMAuthenticator(key)
    tts = TextToSpeechV1(authenticator=authenticator)
    tts.set_service_url(url)

    # Reading from a File
    with open('output.txt', 'r') as f:
        text = f.readlines()

    # replace of  " to space
    text = [line.replace('"', '') for line in text]
    text = ''.join(str(line) for line in text)

    # output as mp3 file
    with open('./voiceReply.mp3', 'wb') as audio_file:
        res = tts.synthesize(text, accept='audio/mp3', voice='en-GB_JamesV3Voice').get_result()
        audio_file.write(res.content)


def play_reply():
    playsound('voiceReply.mp3')
    # this print just to clear the channel
    print(" ")


def main():
    # Connect to websocket interfaces
    headers = {}
    userpass = ":".join(get_auth())
    headers["Authorization"] = "Basic " + base64.b64encode(
        userpass.encode()).decode()
    url = get_url()

    # If you really want to see everything going across the wire,
    # uncomment this. However realize the trace is going to also do
    # things like dump the binary sound packets in text in the
    # console.
    #
    # websocket.enableTrace(True)
    ws = websocket.WebSocketApp(url,
                                header=headers,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.args = parse_args()
    # This gives control over the WebSocketApp. This is a blocking
    # call, so it won't return until the ws.close() gets called (after
    # 6 seconds in the dedicated thread).
    ws.run_forever()
    #----------------------------------
    on_close(ws)
    # calling function to convert to speech
    convert_to_voice()
    play_reply()


if __name__ == "__main__":
    main()
