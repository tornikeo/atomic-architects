FROM python:3.8-bullseye
RUN apt update && apt install ffmpeg -y
RUN  apt install tesseract-ocr libtesseract-dev -y
WORKDIR /workdir
COPY requirements.txt .
RUN pip3 install -r requirements.txt
RUN pip3 install matplotlib>=3.2.2
RUN pip3 install scipy

RUN pip3 install jupyterlab

# Fix for not nbconvert not working
RUN pip3 install nbconvert==6.4.0
RUN pip install -I jinja2==3.0.3
RUN pip3 install scikit-image

# COPY marker.png .
# COPY mask.png .
# COPY utils.py .
COPY main.py .
COPY main.ipynb .
# COPY visualize.ipynb .
# CMD python main.py