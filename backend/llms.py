from openai import OpenAI


# % Shell class to adapt for any model
class LLMShell():
    def __init__(self, **kwargs):
        """
        Arguments:
            1) **kwargs (dictionary): keyword as parameter, value as value
                a. Use whatever kwargs you want to set up your model.
            
        Description:
            Use this shell structure to adapt the Agents to work with any LLM.
            
        Notes:
            You can initialize with whatever you want to fit your LLM of choice. The only thing that has to 
            remain constant is that this class must have a .query() method that takes in only one argument (prompt)
            and returns a string.         
            
        """
        # Change all below to fit your LLM
        pass
        
    def query(self, prompt: str) -> str:
        """
        Arguments:
            1) prompt (string): Question to pass into LLM
        
        Description:
            Sends prompt to LLM and returns answer as string
        
        Returns:
            1) string
        
        """
        # Change below to work with your LLM
        #
        #

        # Return string only
        #
        # 
        #

# % Custom Models
class OpenAILLM():
    def __init__(self, apikey: str, model: str = 'gpt-4o-mini', temperature: float = 1):
        """
        Arguments:
            1) apikey (string): Your OpenAI API key
            2) model (string): the OpenAI model variant you wish to use
                a. gpt-4o, gpt-4-turbo, gpt-4, and gpt-3.5-turbo
                b. https://platform.openai.com/docs/models/continuous-model-upgrades
            3) temperature (bounded float): How creative you want the model to be 
                a. 0 <= temp <= 2
                    i. 0 implies no creativity - will always return the same response
                    ii. 2 implies extreme creativity - God help you 
            
        Description:
            Use this shell structure to adapt the Agents to work with any LLM.
            
        Notes:
            You can initialize with whatever you want to fit your LLM of choice. The only thing that has to 
            remain constant is that this class must have a .query() method that takes in only one argument (prompt)
            and returns a string.
            
        Example:
            with open("C:\\Users\\username\\Desktop\\openai api key.txt", 'r', encoding='utf8') as file:
                api_key = file.read()

            openai.api_key = api_key
            llm = OpenAILLM(apikey=api_key, model='gpt-4o', temperature=1)   
            llm.query("How much does a blue whale weigh?")  
            
        """
        # Build client
        self.client_ = OpenAI(api_key=apikey)

        # Set args
        self.model_ = model
        self.temperature_ = temperature
        
    def query(self, prompt, system_role: str = None, response_format = None):
        """
        Arguments:
            1) prompt (string or list of dict): If string, question to pass into LLM; if dict, anticipates conversation
                a. if dict, format requires [{"role": "system", "content": "You are a venture capitalist"}, 
                                             {"role": "user", "content": "pitch here"}, 
                                             {"role": "venture capitalist", "content": "question about the pitch"}]
            2) system_role (string): The AI role prompt you wish to provide the LLM to give it a defined character role.
            3) response_format (class): Pydantic class of required structure
        
        Description:
            Sends prompt to LLM and returns answer as string
        
        Returns:
            1) string
            
        Example:
            with open("C:\\Users\\username\\Desktop\\openai api key.txt", 'r', encoding='utf8') as file:
                api_key = file.read()

            openai.api_key = api_key
            llm = OpenAILLM(apikey=api_key, model='gpt-4o', temperature=1)   
            llm.query("How much does a blue whale weigh?")  
        
        """
        # Stock role
        if system_role is None:
            system_role = "You are a helpful AI assistant."

        # Build response
            # query base
        pack = {'model':self.model_,
                'temperature':self.temperature_}
            # messages for single shot prompt vs ongoing conversation
        if type(prompt) == str:
            pack['messages'] = [{"role": "system", "content": system_role},
                                {"role": "user", "content": prompt}]
        else:
            pack['messages'] = prompt
            # json or stock text response
        if response_format is not None:
            pack['response_format'] = response_format 
            self.response_ = self.client_.beta.chat.completions.parse(model = pack['model'],
                                                                      temperature = pack['temperature'],
                                                                      messages = pack['messages'],
                                                                      response_format = pack['response_format'])
            return self.response_.choices[0].message.parsed
        else:
            self.response_ = self.client_.chat.completions.create(**pack)
            return self.response_.choices[0].message.content
    
        # if response_format is not None:
        #     return response.choices[0].message.content
        # else:
        #     return response.choices[0].message.parsed