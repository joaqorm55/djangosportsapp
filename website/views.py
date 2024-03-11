from django.shortcuts import render, HttpResponse, redirect
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from PIL import Image, ImageDraw, ImageOps, ImageFont
from openai import OpenAI
from io import BytesIO
import camelot
import pandas as pd
import os
import json
import janitor
import re

example_json = {
  "type": "object",
  "properties": {
      "team_info": {
      "type": "object",
      "properties": {
        "Team_1": { "type": "string"},
        "Team_2": { "type": "string" },
      },
      "required": ["Team_1", "Team_2"]
    },
    "game_info": {
      "type": "object",
      "properties": {
        "date": { "type": "string", "format": "date" },
        "location": { "type": "string" },
        "attendance": { "type": "integer" }
      },
      "required": ["Date", "Location", "Attendance"]
    },
    "Scoring Summary": {
      "type": "object",
      "properties": {
        "Team_1": { "type": "integer" },
        "Team_2": { "type": "integer" },
        "Goals": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "Time": { "type": "string" },
              "Team": { "type": "string" },
              "Scorer": { "type": "string" },
              "Assist": {
                "type": "array",
                "items": { "type": "string" }
              }
            },
            "required": ["Time", "Team", "Scorer"]
          }
        }
      },
      "required": ["Team_1", "Team_2", "Goals"]
    },
    "Team_Comparison": {
      "type": "object",
      "properties": {
        "Shots": {
          "type": "object",
          "properties": {
            "Team_1": { "type": "integer" },
            "Team_2": { "type": "integer" }
          },
          "required": ["Team_1", "Team_2"]
        },
        "Shots_on_Goal": {
          "type": "object",
          "properties": {
            "Team_1": { "type": "integer" },
            "Team_2": { "type": "integer" }
          },
          "required": ["Team_1", "Team_2"]
        },
        "Corners": {
          "type": "object",
          "properties": {
            "Team_1": { "type": "integer" },
            "Team_2": { "type": "integer" }
          },
          "required": ["Team_1", "Team_2"]
        },
        "Goals": {
          "type": "object",
          "properties": {
            "Team_1": { "type": "integer" },
            "Team_2": { "type": "integer" }
          },
          "required": ["Team_1", "Team_2"]
        },
        "Saves": {
          "type": "object",
          "properties": {
            "Team_1": { "type": "integer" },
            "Team_2": { "type": "integer" }
          },
          "required": ["Team_1", "Team_2"]
        },
        "Fouls": {
          "type": "object",
          "properties": {
            "Team_1": { "type": "integer" },
            "Team_2": { "type": "integer" }
          },
          "required": ["Team_1", "Team_2"]
        }
      },
      "required": ["Shots", "Shots on Goal", "Corners", "Goals", "Saves", "Fouls"]
    },
    "Cautions and Ejections": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "Time": { "type": "string" },
          "Player": { "type": "string" },
          "Team": { "type": "string" },
          "Card": { "type": "string" }
        },
        "required": ["Time", "Player", "Team", "Card"]
      }
    }
  },
  "required": ["Game Info", "Scoring Summary", "Team Comparison", "Cautions and Ejections"]
}


def home(request):
    return render(request, "home.html" )

def about(request):
    return render(request, "about.html")

def uploadpage(request):
    context = {}
    if request.method == 'POST':
        uploaded_file = request.FILES['document']
        print(uploaded_file.name)
        print(uploaded_file.size)
        fs = FileSystemStorage()
        name = fs.save(uploaded_file.name, uploaded_file)
        context['url'] = fs.url(name)
        
        
        api_key = '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'
        client = OpenAI(api_key=api_key)
        
        file = client.files.create(
            file = open(f"media\{uploaded_file.name}", "rb"),
            purpose="assistants"
        )

        assistant_file = client.beta.assistants.files.create(
            assistant_id="asst_6hmR3DZ1wfsVBURMhvwldUME",
            file_id= file.id
        )

        context['assistant'] = assistant_file.id

        run = client.beta.threads.create_and_run(
            assistant_id="asst_Y7PEZIV6x2rUWu7hIM8qJKKY",
            thread={
            "messages": [
                {"role": "user", "content": f" using this file id - {file.id} can you give me a MainJSON output of the scoring summary, attendance, shots, shots on goal, corners, and other high level stats that compare both teams. The Data schema should be like this -" + json.dumps(example_json) + " extract the actual data from the uploaded file to match this structure."}
            ]
            }
        )

        while True:
            run = client.beta.threads.runs.retrieve(
            thread_id=run.thread_id,
            run_id=run.id
        )
            if run.status == 'completed':
                messages = client.beta.threads.messages.list(
                thread_id = run.thread_id
                )
                print(messages)

                # json_match = re.search(r'```json(.*?)```', messages.data[0].content[0].text.value, re.DOTALL)
                # json_string = json_match.group(1).strip()
                # game_summary_dict = json.loads(json_string)
                
                # context = {'summary': game_summary_dict}
                context['message'] = messages.data[0].content[0].text.value
                print(messages.data[0].content[0].text.value)

            
                break
  
            else:
                print("Run still in progress. Waiting...")

    return render(request, "uploadpage.html", context)



def uploadimage(request):
    context = {}
    if request.method == 'POST':
        uploaded_file = request.FILES['document']
        print(uploaded_file.name)
        print(uploaded_file.size)
        fs = FileSystemStorage()
        name = fs.save(uploaded_file.name, uploaded_file)
        context['url'] = fs.url(name)
        
        #PIL Image manipulation
        for_image_path = fs.path('socialmedia/foreground.png')
        back_image_path = fs.path(name)
        # Open the images
        background = Image.open(back_image_path)
        foreground = Image.open(for_image_path)
        
        background.paste(foreground, (0, 0), foreground)
        image_io = BytesIO()
        background.save(image_io, format='png', quality=80) # you can change format and quality

        # Resize the foreground to match the size of the background
        # foreground = foreground.resize(background.size, Image.Resampling.LANCZOS)

        # # Add a grey overlay to the background

        # # Calculate the position to place the foreground in the center of the background
        # position = ((background.width - foreground.width) // 2, (background.height - foreground.height) // 2)

        # # Paste the foreground onto the background
        # background.paste(foreground, position, foreground)

        resized_image_path = fs.save('resized_' + uploaded_file.name, ContentFile(image_io.getvalue()))
        context['url2'] = fs.url(resized_image_path)
    
    return render(request, "uploadimage.html", context)

# Create your views here.


def gamedetails(request):
    data = None
    if request.method == 'POST':
        uploaded_file = request.FILES['document']
        print(uploaded_file.name)
        print(uploaded_file.size)
        fs = FileSystemStorage()
        name = fs.save(uploaded_file.name, uploaded_file)
        url = fs.path(name)
        tab = camelot.read_pdf(url, pages='all', flavor = 'stream', guess = True, multiple_tables= True,row_tol=10)

        print(tab)
        first_table = tab[0].df
        df = pd.DataFrame(first_table)
        cleaned_df = df.clean_names()
        
        data = cleaned_df.to_dict(orient='records')

    return render(request, 'gamedetails.html', {'data': data})

