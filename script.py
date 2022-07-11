import os

keywords = open('shearlock/scraper/keywords/duck2.txt','r')
keyword_list= [line.split("\n")[0] for line in keywords]


for keyword in keyword_list:

    cmd = f'''pipenv run python main_script.py --query "{keyword}" -s --collection "{keyword}"'''
    p_cmd = f'cmd /c "{cmd}"'
    print(p_cmd)
    os.system(p_cmd)

# f'''pipenv run python main_script.py --query "food science" --all'''
# f''' pipenv run python main_script.py --keywords duck2.txt --subject "food science"  -s --collection "duck2_ma"'''

