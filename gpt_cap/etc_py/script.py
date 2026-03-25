import json

def extract_relevant_descriptors(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cleaned_data = {}

    for device, services in data.items():
        new_services = {}
        for service_name, service_info in services.items():
            cleaned_info = {}
            for key in service_info:
                if key in ["descriptor", "return_descriptor", "argument_descriptor"]:
                    cleaned_info[key] = service_info[key]
            if cleaned_info:  # Only include services that have at least one relevant field
                new_services[service_name] = cleaned_info

        if new_services:  # Only include devices that have at least one service
            cleaned_data[device] = new_services

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

# 사용 예시
extract_relevant_descriptors('service_list_ver1.5.3.json', 'service_list_ver1.5.4.json')
