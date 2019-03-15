from bs4 import BeautifulSoup
from os import listdir
import requests as r
import os.path
import sys
import re

class PS2Saves(object):
	def __init__(self, game_id):
		self.game_id = game_id.upper()

	def get_game_name_by_id(self):
		with open("PS2_LIST.csv") as PS2List_file:
			PS2GameList = PS2List_file.read()

		if self.game_id in PS2GameList:
			self.game_name = PS2GameList.split(self.game_id + ",")[1].split("\n")[0]
		else:
			self.game_name = None
		return self.game_name

	def get_game_name_by_id2(self): #FALLBACK IF NO ID WAS FOUND WITH GET_NAME_BY_ID

		what_to_send = """
		<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
		    <s:Body>
		        <GetGameNameById xmlns="http://oplmanager.no-ip.info/" xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
		            <GameId>%s</GameId>
		        </GetGameNameById>
		    </s:Body>
		</s:Envelope>
		""" % self.game_id
		
		headers = {
			"Content-Type": 'text/xml',
		}

		response = r.post("http://oplmanager.no-ip.info/API/V4/OplManagerService.asmx", data=what_to_send, headers=headers)
		
		try:
			self.game_name = response.content.split("GetGameNameByIdResult>")[1][:-2]
		except IndexError:
			return False

		return self.game_name.lower()

	def get_saves_url(self):
		if 'game_name' not in dir(self): return False

		game_name = self.game_name

		headers = {
			"User-Agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3178.0 Safari/537.36",
			'Referer': 'https://gamefaqs.gamespot.com/',
			'Host': 'gamefaqs.gamespot.com',
			'Content-Type': 'application/x-www-form-urlencoded'
		}

		payload = {
			'game_type': '0',
			'game': game_name,
			'platform': 94,
			'distribution': 0,
			'category': 0,
			'date_type': 0,
			'date_1': None,
			'date_2':None,	
			'date_year':0,
			'contents_type': 0,
			'contents': 0,
			'region_type': 0,
			'region': 0,
			'company_type': 0,
			'company_text':None,
			'company':None,
			'sort':0,
			'min_scores':0
		}

		requestReturning = r.post('https://gamefaqs.gamespot.com/search_advanced', headers=headers, data=payload)

		textAnalyzedByBeautifulSoup = BeautifulSoup(requestReturning.text, 'lxml')

		allTheLinks = textAnalyzedByBeautifulSoup.find('div', class_='search_results_product').find_all('div', class_='sr_row')

		
		if len(allTheLinks) >= 10:
			numero_de_jogos = 10
		elif 0 > len(allTheLinks) < 10:
			numero_de_jogos = len(allTheLinks) + 1
		else:
			return False
		
		all_games = {}
		
		for n in range(numero_de_jogos):
			gameName = allTheLinks[n].find('div', class_='sr_title').string

			savesFromGame1 = [ game_url['href'] for game_url in allTheLinks[n].find('div', class_='sr_links').children if game_url.string == 'Saves']

			savesFromGame = savesFromGame1[0] if len(savesFromGame1) >= 1 else None
			
			if savesFromGame: all_games[n] = (gameName, savesFromGame) #all_games.append((gameName, savesFromGame))

		self.all_games = all_games
		return all_games

	def get_available_saves(self, number):
		REGION_CODE_DICTIONARY = {
			"SLUS": 'North America',
			'SCUS': 'North America',

			"SCES": "Europe",
			"SLES": "Europe",

			"SLPS": "Japan",
			"SLKA": "Japan",
			"SLPM": "Japan",
			"SCPS": "Japan",

			"SCCS": "China",

		}

		baseUrl = "https://gamefaqs.gamespot.com"

		gameToGet = self.all_games[number]

		wholeUrlToGet = baseUrl + gameToGet[1]
		headers = {
			"User-Agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3178.0 Safari/537.36",
			'Referer': 'https://gamefaqs.gamespot.com/',
			'Host': 'gamefaqs.gamespot.com',
			'Content-Type': 'application/x-www-form-urlencoded'
		}

		responseFromUrl = r.get(wholeUrlToGet, headers=headers).text

		mainSoup = BeautifulSoup(responseFromUrl, 'lxml')

		savesDiv = mainSoup.find('div', class_='span8')
		all_saves = savesDiv.find_all('div', class_='pod')[:-1]

		savesToReturn = {}
		for save in all_saves:
			saveCategory = save.div.h2.string

			if REGION_CODE_DICTIONARY[self.game_id[:4]] not in saveCategory:
				continue
			
			if saveCategory not in savesToReturn:
				savesToReturn[saveCategory] = {}

			savesInThisCategory = save.find('table', class_='saves').tbody

			turn = 1
			numberOfSaves = 0
			for save in savesInThisCategory:
				if turn == 1:
					saveUrl = baseUrl + save.td.a.get('href')
					saveSize = save.td.next_sibling.next_sibling.next_sibling.string + "B"

					savesToReturn[saveCategory][numberOfSaves] = [saveUrl, saveSize]
					
					turn = 2

				elif turn == 2:
					saveDescription = save.string

					savesToReturn[saveCategory][numberOfSaves].append(saveDescription)

					numberOfSaves += 1
					turn = 1

		self.savesToReturn = savesToReturn
		return savesToReturn

	def download_save(self, urlToDownload, output_name):
		headers = {
			"User-Agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3178.0 Safari/537.36",
			'Referer': 'https://gamefaqs.gamespot.com/',
			'Host': 'gamefaqs.gamespot.com',
			'Content-Type': 'application/x-www-form-urlencoded'
		}

		request = r.get(urlToDownload, headers=headers)

		fileName = request.headers['content-disposition'].split("filename=\"")[1][:-1]
		
		if output_name:
			fileName = output_name + '.' + fileName.split(".")[-1]

		if (fileName in listdir(".")):
			print("Arquivo \"%s\" ja existe!" % fileName)
			sys.exit(1)
		
		try:
			with open(fileName, 'wb') as fileToWrite:
				fileToWrite.write(request.content)
		except Exception as e:
			return None
		else:
			return("%s salvo com exito!" % fileName)


def is_code_valid(game_code):
	return re.match(r"^\w{4,4}_\d{3,3}\.\d{2,2}$", game_code)

def get_input_data():
	if len(sys.argv) < 2:
		print(('S.O.S. Save2Me v1.0-init\n'
'USO:\n'
'	%s CODIGO_DO_JOGO [-o NOME_DO_ARQUIVO]\n\n'
'***********************************************\n'
'	CODIGO_DO_JOGO:     Deve ser a id do jogo (como SLUS_123.45), no estilo "AAAA_111.11"\n\n'
'	-o NOME_DO_ARQUIVO: Especifica o nome do arquivo de save') % os.path.basename(sys.argv[0]))
		sys.exit(1)

	game_code = sys.argv[1]

	if not is_code_valid(game_code):
		print("Insira um codigo do jogo no seguinte formato:\n\t###_***.**, onde # indica qualquer letra e * qualquer numero.")
		sys.exit(1)

	if '-o' in sys.argv:
		if sys.argv[-1] != '-o':
			output = sys.argv[-1]
		else:
			output = None
			print ("******* ARQUIVO DE SAIDA ALTERADO *******")
	else:
		output = None

	return game_code, output

def choose_game(available_games):
	print("Por favor, escolha um jogo da lista.")
	for game_id in available_games:
		name_of_this_game = available_games[game_id][0]
		print("\t[%d] %s" % (game_id, name_of_this_game))

	which_game = int(input("Insira aqui o numero referente ao jogo que voce quer: "))

	return which_game

def choose_save(available_saves):
	first_loop_index = 0
	second_loop_index = 0
	
	saves_to_choose = {}
	for category in available_saves:
		alphabet = "ABCDEFGHIJKLMOPQRSTUVWXYZ"

		print(category)
		for save_x in available_saves[category]:
			numbers = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
			certain_game = available_saves[category][save_x]

			saves_to_choose[alphabet[first_loop_index] + numbers[second_loop_index]] = certain_game[0]

			print('[%s] DETALHES DO SAVE:\n\tURL do Save: %s\n\tTamanho do save: %s\n\tDescricao (em ingles): %s\n' % (alphabet[first_loop_index] + numbers[second_loop_index],
				certain_game[0], certain_game[1], certain_game[2]))

			second_loop_index += 1

		first_loop_index += 1
		second_loop_index = 0

	print("#####"*10)

	if (int(sys.winver[0]) < 3):
		which_save = raw_input("\nInsira o codigo (entre colchetes '[...]') referente ao save que voce quer: ")
	else:
		which_save = str(input("\nInsira o codigo (entre colchetes '[...]') referente ao save que voce quer: "))

	return saves_to_choose, which_save

def main():
	game_code, output = get_input_data()
	save = PS2Saves(game_code)
	
	game_name = save.get_game_name_by_id()
	if not game_name:
		game_name = save.get_game_name_by_id2()
	available_games = save.get_saves_url()
	which_game = choose_game(available_games)
	
	print("\n\n")

	available_saves = save.get_available_saves(which_game)
	saves_to_choose, which_save = choose_save(available_saves)
	is_sucessful = save.download_save(saves_to_choose[which_save.upper()], output)

	if is_sucessful:
		print(is_sucessful + " salvo com exito!")
	else:
		print("Algo aconteceu de errado!")
		sys.exit(1)

if __name__ == '__main__':
	main()