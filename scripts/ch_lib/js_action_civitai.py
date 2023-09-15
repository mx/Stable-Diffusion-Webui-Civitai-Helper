# -*- coding: UTF-8 -*-
# handle msg between js and python side
import os
import json
import requests
import webbrowser
from modules.shared import opts
from . import util
from . import model
from . import civitai
from . import msg_handler
from . import downloader



# get civitai's model url and open it in browser
# parameter: model_type, search_term
# output: python msg - will be sent to hidden textbox then picked by js side
def open_model_url(msg):
    util.printD("Start open_model_url")

    output = ""
    result = msg_handler.parse_js_msg(msg)
    if not result:
        util.printD("Parsing js ms failed")
        return

    model_type = result["model_type"]
    search_term = result["search_term"]

    model_info = civitai.load_model_info_by_search_term(model_type, search_term)
    if not model_info:
        util.printD(f"Failed to get model info for {model_type} {search_term}")
        return ""

    if "modelId" not in model_info.keys():
        util.printD(f"Failed to get model id from info file for {model_type} {search_term}")
        return ""

    model_id = model_info["modelId"]
    if not model_id:
        util.printD(f"model id from info file of {model_type} {search_term} is None")
        return ""

    url = f'{civitai.URLS["modelPage"]}{model_id}'


    # msg content for js
    content = {
        "url":""
    }

    if not opts.ch_open_url_with_js:
        util.printD(f"Open Url: {url}")
        # open url
        webbrowser.open_new_tab(url)
    else:
        util.printD("Send Url to js")
        content["url"] = url
        output = msg_handler.build_py_msg("open_url", content)

    util.printD("End open_model_url")
    return output



# add trigger words to prompt
# parameter: model_type, search_term, prompt
# return: [new_prompt, new_prompt] - new prompt with trigger words, return twice for txt2img and img2img
def add_trigger_words(msg):
    util.printD("Start add_trigger_words")

    result = msg_handler.parse_js_msg(msg)
    if not result:
        util.printD("Parsing js ms failed")
        return

    model_type = result["model_type"]
    search_term = result["search_term"]
    prompt = result["prompt"]


    model_info = civitai.load_model_info_by_search_term(model_type, search_term)
    if not model_info:
        util.printD(f"Failed to get model info for {model_type} {search_term}")
        return [prompt, prompt]

    if "trainedWords" not in model_info.keys():
        util.printD(f"Failed to get trainedWords from info file for {model_type} {search_term}")
        return [prompt, prompt]

    trainedWords = model_info["trainedWords"]
    if not trainedWords:
        util.printD(f"No trainedWords from info file for {model_type} {search_term}")
        return [prompt, prompt]

    if len(trainedWords) == 0:
        util.printD(f"trainedWords from info file for {model_type} {search_term} is empty")
        return [prompt, prompt]

    # guess if trained words are a list of words or list of prompts
    prompt_list = (',' in trainedWords[0])

    # if a list of prompts, join with a newline, else a comma and a space
    trigger_words = ("\n" if prompt_list else ", ").join(trainedWords)

    new_prompt = f"{prompt} {trigger_words}"
    util.printD(f"trigger_words: {trigger_words}")
    util.printD(f"prompt: {prompt}")
    util.printD(f"new_prompt: {new_prompt}")

    util.printD("End add_trigger_words")

    # add to prompt
    return [new_prompt, new_prompt]



# use preview image's prompt as prompt
# parameter: model_type, model_name, prompt, neg_prompt
# return: [new_prompt, new_neg_prompt, new_prompt, new_neg_prompt,] - return twice for txt2img and img2img
def use_preview_image_prompt(msg):
    util.printD("Start use_preview_image_prompt")

    result = msg_handler.parse_js_msg(msg)
    if not result:
        util.printD("Parsing js ms failed")
        return

    model_type = result["model_type"]
    search_term = result["search_term"]
    prompt = result["prompt"]
    neg_prompt = result["neg_prompt"]


    model_info = civitai.load_model_info_by_search_term(model_type, search_term)
    if not model_info:
        util.printD(f"Failed to get model info for {model_type} {search_term}")
        return [prompt, neg_prompt, prompt, neg_prompt]

    if "images" not in model_info.keys():
        util.printD(f"Failed to get images from info file for {model_type} {search_term}")
        return [prompt, neg_prompt, prompt, neg_prompt]

    images = model_info["images"]
    if not images:
        util.printD(f"No images from info file for {model_type} {search_term}")
        return [prompt, neg_prompt, prompt, neg_prompt]

    if len(images) == 0:
        util.printD(f"images from info file for {model_type} {search_term} is empty")
        return [prompt, neg_prompt, prompt, neg_prompt]

    # get prompt from preview images' meta data
    preview_prompt = ""
    preview_neg_prompt = ""
    for img in images:
        if "meta" in img.keys():
            if img["meta"]:
                if "prompt" in img["meta"].keys():
                    if img["meta"]["prompt"]:
                        preview_prompt = img["meta"]["prompt"]

                if "negativePrompt" in img["meta"].keys():
                    if img["meta"]["negativePrompt"]:
                        preview_neg_prompt = img["meta"]["negativePrompt"]

                # we only need 1 prompt
                if preview_prompt:
                    break

    if not preview_prompt:
        util.printD(f"There is no prompt of {model_type} {search_term} in its preview image")
        return [prompt, neg_prompt, prompt, neg_prompt]

    util.printD("End use_preview_image_prompt")

    return [preview_prompt, preview_neg_prompt, preview_prompt, preview_neg_prompt]


# download model's new verson by model path, version id and download url
# output is a md log
def dl_model_new_version(msg, max_size_preview, skip_nsfw_preview):
    """ This method is triggered by a click event on the client
        side that sends a signal to download a single new model
        version. The actual check for new models is in
        `model_action_civitai.check_models_new_version_to_md`.

        XXX: Perhaps it should be moved to this file?
    """
    util.printD("Start dl_model_new_version")

    output = ""

    result = msg_handler.parse_js_msg(msg)
    if not result:
        output = "Parsing js msg failed"
        util.printD(output)
        return output

    model_path = result["model_path"]
    version_id = result["version_id"]
    download_url = result["download_url"]
    model_type = result["model_type"]

    util.printD(f"model_path: {model_path}")
    util.printD(f"version_id: {version_id}")
    util.printD(f"download_url: {download_url}")

    # check data
    if not model_path:
        output = "model_path is empty"
        util.printD(output)
        return output

    if not version_id:
        output = "version_id is empty"
        util.printD(output)
        return output

    if not download_url:
        output = "download_url is empty"
        util.printD(output)
        return output

    if not os.path.isfile(model_path):
        output = f"model_path is not a file: {model_path}"
        util.printD(output)
        return output

    # get model folder from model path
    model_folder = os.path.dirname(model_path)

    # download file
    new_model_path = downloader.dl(download_url, model_folder, None, None)
    if not new_model_path:
        output = f"Download failed, check console log for detail. Download url: {download_url}"
        util.printD(output)
        return output

    # get version info
    version_info = civitai.get_version_info_by_version_id(version_id)

    # now write version info to files
    model.process_model_info(new_model_path, version_info, model_type)

    # then, get preview image
    civitai.get_preview_image_by_model_path(new_model_path, max_size_preview, skip_nsfw_preview)

    output = f"Done. Model downloaded to: {new_model_path}"
    util.printD(output)
    return output
