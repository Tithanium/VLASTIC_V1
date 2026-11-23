from configparser import ConfigParser
from collections import namedtuple
import os

class Config(object):
    """
    Read configuration from ini file.
    The configuration will be used for storing
    The file is automatically converted to the structure (one level above dictionary)

    """
    def __init__(self,path_load,path_save_list_express):
        self._path_load=path_load
        self._path_save=path_load
        self._path_save_list = path_save_list_express

        self.__dictionary = ConfigParser()
        self.__dictionary.read(self._path_load)
        self.config_to_attributes() # convert the dictionary into a structure
        self.default_plot.color_plot_board
        ##ecriture du fichier dans self._path_save_list pour illustrer les chemins crées
        self.write_names()

        ## accède aux données de deux manières différentes
        #self.dictionary['DEFAULT_INI']['nb_tours_per_test']
        #self.DEFAULT_INI.nb_tours_per_test

    def save(self):
        self.attributes_to_config()  # transfert the structure modifications to the dictionary

        # Write changes back to file
        with open(self._path_save, 'w') as conf:
            self.__dictionary.write(conf)

    def write_names(self):
        # Ouvrir le fichier en mode écriture ('w')
        with open(self._path_save_list, 'w') as fichier:
            for sections in self.__dictionary.sections():
                section_nom = sections.lower()
                [section_nom,digit_sec]=self.extract_last_string_digit(section_nom)
                for subsection in self.__dictionary[sections]:
                    data_conv = self.convertir_str_to_data(self.__dictionary[sections][subsection])
                    sub_nom=subsection.lower()
                    [sub_nom, digit_sub] = self.extract_last_string_digit(sub_nom)

                    if digit_sub is None:
                        if digit_sec is None:
                            name="self.%s.%s\n" %(section_nom,sub_nom)
                        else:
                            name = "self.%s[%d].%s\n" % (section_nom, digit_sec, sub_nom)
                    else:
                        if digit_sec is None:
                            name = "self.%s.%s[%d]\n" % (section_nom, sub_nom,digit_sub)
                        else:
                            name = "self.%s[%d].%s[%d]\n" % (section_nom, digit_sec, sub_nom,digit_sub)

                            # Écrire une chaîne de caractères dans le fichier

                    fichier.write(name)

    def convertir_data_to_str(self, data):
        # convertion des données (différent type possible) en chaine de caractère pour sauvegarde
        if isinstance(data, bool):
            if data==True:
                Chaine = 'True'
            else:
                Chaine = 'False'
        elif data==None:
            Chaine = 'None'
        else:
            if type(data) is tuple:
                Chaine = '(' + ','.join(str(item) for item in data)  + ')'
            else:
                Chaine = str(data)

        return Chaine

    def convertir_str_to_data(self,Chaine):

        # convertion de la chaine de caractere du dictionaire dans son type
            # si l'output recherché est un booléan de valeur true, false ou none
            if Chaine.lower()=='true':
                return True
            elif Chaine.lower() =='false':
                return False
            elif Chaine.lower() =='none':
                return None
            else:
                try:
                    return int(Chaine)       # Essayer de convertir en float
                except ValueError:
                    try:
                        return float(Chaine)
                    except ValueError:
                        # Si ce n'est pas un float, essayer de convertir en liste
                        # try:
                        #     return eval(Chaine)
                        # except:
                        #     # Si ce n'est pas une liste non plus, retourner la donnée telle quelle
                        #     return Chaine
                        try:
                            # Vérifier si la chaîne contient des virgules
                            if ',' in Chaine:
                                # Utiliser eval pour créer un tuple
                                elements = Chaine.strip('()').split(',')
                                # Convertir chaque élément en int, float ou laisser tel quel
                                converted_elements = []
                                for element in elements:
                                    try:
                                        converted_elements.append(int(element))
                                    except ValueError:
                                        try:
                                            converted_elements.append(float(element))
                                        except ValueError:
                                            converted_elements.append(element)
                                return tuple(converted_elements)
                            else:
                                # Sinon, retourner la donnée telle quelle
                                return Chaine
                        except:
                            # Si ce n'est pas une liste non plus, retourner la donnée telle quelle
                            return Chaine
    def extract_last_string_digit(self, chaine):
        digit = None
        chaine_maitresse = chaine
        if chaine[-1].isdigit():
            i = len(chaine) - 1
            while i >= 0:
                i -= 1
                if not chaine[i].isdigit():
                    break
            i +=1
            digit = int(chaine[i:])
            chaine_maitresse = chaine[0:i]
        return  chaine_maitresse, digit

    def config_to_attributes(self):
        # écriture des valeurs lues dans le fichier de configuration dans la structure self.
        # creation des valeurs
        # self.section1.subsection1=value
        # self.section1.subsection2=value
        # etc
        for sections in self.__dictionary.sections():
            section_nom = sections.lower()
            [section_nom,digit_sec]=self.extract_last_string_digit(section_nom)

            # création de la sous_structure "sub_struct" momentanée
            # qui sera stockée en tant que "section1"
            sub_struct = type('MyClass', (), {})()
            for subsection in self.__dictionary[sections]:
                data_conv = self.convertir_str_to_data(self.__dictionary[sections][subsection])
                sub_nom=subsection.lower()
                [sub_nom, digit_sub] = self.extract_last_string_digit(sub_nom)

                if digit_sub is None:
                    sub_struct.__setattr__(sub_nom,data_conv)
                else:
                    if hasattr(sub_struct, sub_nom):
                        taille_current_table=len(getattr(sub_struct, sub_nom))
                        if taille_current_table <= digit_sub+1:
                            getattr(sub_struct,sub_nom).extend([None] * (digit_sub - taille_current_table+1))
                    else:
                        sub_struct.__setattr__(sub_nom, [None]*(digit_sub+1))
                    getattr(sub_struct, sub_nom)[digit_sub]=data_conv

            #sauvegarde de la substructure dans la structure globale
            if digit_sec is None:
                 self.__setattr__(section_nom, sub_struct)
            else:
                 if hasattr(self, section_nom):
                     taille_current_table = len(getattr(self, section_nom))
                     if taille_current_table <= digit_sec:
                         getattr(self, section_nom).extend([None] * (digit_sec - taille_current_table+1))
                 else:
                     self.__setattr__(section_nom, [None] * (digit_sec+1))
                 getattr(self, section_nom)[digit_sec] = sub_struct
                # self.arduino

    def attributes_to_config(self):
        # si des valeurs de la structures ont été modifiées, elles sont implémentées dans le dictionaire
        self.differences=[]
        for sections in self.__dictionary.sections():
            section_nom = sections.lower()
            [section_nom, digit_sec] = self.extract_last_string_digit(section_nom)

            for subsection in self.__dictionary[sections]:
                sub_nom=subsection.lower()
                [sub_nom, digit_sub] = self.extract_last_string_digit(sub_nom)

                if digit_sub is None:
                    if digit_sec is None:
                        data = self.__getattribute__(section_nom).__getattribute__(sub_nom)
                    else:
                        data = self.__getattribute__(section_nom)[digit_sec].__getattribute__(sub_nom)
                else:
                    if digit_sec is None:
                        data = self.__getattribute__(section_nom).__getattribute__(sub_nom)[digit_sub]
                    else:
                        data = self.__getattribute__(section_nom)[digit_sec].__getattribute__(sub_nom)[digit_sub]

                data_conv=self.convertir_data_to_str(data)
                initial_data= self.__dictionary[sections][subsection]
                self.__dictionary[sections][subsection]=data_conv
                if initial_data !=data_conv:
                    self.differences.append([sections, subsection, initial_data, data_conv])