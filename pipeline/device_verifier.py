import re
from difflib import SequenceMatcher
from .SERVICE_DESCRIPTION_FINAL import description

class Mapping_Verifier:
    def __init__(self, input_text):
        self.input_text = input_text
        self.value_dict = {}
        self.func_dict = {}
        self.device_list = []
        self.error_message = "Error : "
        self.data = description.copy()
    def remove_spaces(self, match):
        return match.group(0).replace(" ", "") + " "
    def device_verify(self):
        self.input_text = re.sub(r"(\(\#[^\(\)]*\))", self.remove_spaces, self.input_text)
        device_pattern = r"\(\#([^\(\)]*)\)"
        self.device_list = re.findall(device_pattern, self.input_text)
        for i, device in enumerate(self.device_list):
            if (device not in self.data):
                new_device = self.device_validation_modification_by_sequencematcher(device, 0.3) 
                if (new_device == None):
                    self.input_text = re.sub(rf"(\(\#{device}\))", "", self.input_text)
                else:
                    self.input_text = self.input_text.replace(device,new_device)
    def modify_input_and_data(self):
        clean_input = re.sub(r'[^a-zA-Z]', ' ', self.input_text)
        substrings = ['if', 'the', 'a','and','it','on', 'at', 'in', 'over', 'below', 'on', 'off', 'turn' ]
        substrings_pattern = '|'.join(map(re.escape, substrings))
        pattern = rf'(?<!\S)({substrings_pattern})(?!\S)'
        self.input_text = re.sub(pattern, ' ', clean_input.lower())
        for device, desc in self.data.items() :
            clean_description = re.sub(r'[^a-zA-Z]', ' ', desc)
            substrings = ['functions', 'values', 'string','int','double','on', 'off', 'binary']
            substrings_pattern = '|'.join(map(re.escape, substrings))
            pattern = rf'(?<!\S)({substrings_pattern})(?!\S)'
            clean_description = re.sub(pattern, ' ', clean_description.lower())
            self.data[device] = clean_description
    def device_mapping(self):
        self.modify_input_and_data()
        more_devices = []
        split_list = self.input_text.split()
        #make more devices
        for word in split_list:
            modification_result = self.device_validation_modification_by_sequencematcher(word, 0.7)
            if (modification_result is not None and modification_result not in more_devices):
                more_devices.append(modification_result)
            if (modification_result is None):
                devices_from_description  = self.deviceadd_by_description(word, 0.8)
                if (devices_from_description is not None):
                    for device in devices_from_description:
                        if (device not in more_devices):
                            more_devices.append(device)
        #clock의 경우 별도 처리
        if "Clock" not in more_devices :
             more_devices.append("Clock")
        return more_devices
    '''
    def device_validation_modification(self,device, thresold):
        # Find the most similar device name in THING_LIST
        (result, best) = get_most_similar(device, self.data.keys())
        if (best > thresold):
            return result
        else:
            return None
    '''
    def deviceadd_by_description(self,word,thresold):
        candidate_list = []
        for device, description in self.data.items():
            # Replace all non-alphabet characters with space and split into words
            words = description.split()
            most_similar_device = None
            max_similarity = 0
            for desc_word in words:
                similar_device = self.device_validation_modification_by_sequencematcher(desc_word, thresold)
                similarity = SequenceMatcher(None, word.lower(), desc_word.lower()).ratio()
                if similarity > max_similarity:
                    max_similarity = similarity
            if max_similarity >= thresold:
                candidate_list.append(device)
            if len(candidate_list) >= 3:
                return None
        else:
            return candidate_list


        

    def device_validation_modification_by_sequencematcher(self,device, thresold):
        # Find the most similar device name in THING_LIST
        LIST  = list(self.data.keys())

        # 알파벳 수준의 유사성에서 가장 높은 것을 찾음
        # 높은 임계값(0.8 이상): 두 문자열이 매우 유사한 경우만 매칭.
        # 중간 임계값(0.6 - 0.8): 두 문자열이 적당히 유사한 경우 매칭.
        # 낮은 임계값(0.4 - 0.6): 두 문자열이 약간 유사한 경우 매칭.

        most_similar_device = None
        max_similarity = 0
        for thing in LIST:
            similarity = SequenceMatcher(None, device.lower(), thing.lower()).ratio()
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_device = thing

        # Change this threshold to change the similarity threshold
        SIMILARITY_THRESHOLD = thresold

        if most_similar_device and max_similarity >= SIMILARITY_THRESHOLD:
            device_name = most_similar_device
            #print(f"Device name changed to: {device_name}")
            return device_name
        else:
            #print(f"No similar device found in THING_LIST")
            # sys.exit(1)
            return None
   
    