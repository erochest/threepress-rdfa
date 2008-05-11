import processing.opengl.*; 

// Size of our window
int HEIGHT = 600;
int WIDTH = 800;

// Margin between the text and the viewscreen
int MARGIN = 5;

int FONT_SIZE = 48;
int MAX_SIZE = 60;  // Words can get no larger than this size

// Our starting alpha channel (max = 255)
int ALPHA_START = 200;

int totalWords;

// Stop words (e.g. "the", "and")
HashMap stopwords = new HashMap();
PGraphics p;


// Palettes control which color scheme is modified when the
// word "ages"
int RED_PALETTE = 0;
int GREEN_PALETTE = 1;
int BLUE_PALETTE = 2;

int index = 0;
PFont font;

// The total list of words in the document
ArrayList words = new ArrayList();

// The list of words we're displaying in each frame
ArrayList displayWords = new ArrayList();

// The frequencies of all words we've seen to date
HashMap wordMap = new HashMap();

// Words we are already displaying, so don't bother re-displaying them
// (instead increment them in-place)
HashMap displayMap = new HashMap();


String s;
int X_START = MARGIN * 3;
int Y_START = MARGIN * 10;
int x = X_START;
int y = Y_START;
int r = 255;
int g = 255;
int b = 255;

class Word {
  String w;
  int x, y, r, g, b, a;
  int frequency;
  int drift;
  int size = 48;
  int palette;
  int initial_x;
  int initial_y;

  public Word(String w, int x, int y, int r, int g, int b) {
    this.w = w;
    this.x = x; 
    this.initial_x = x;
    this.y = y; 
    this.initial_y = y;
    this.r = r;
    this.g = g;
    this.b = b;
    this.a = ALPHA_START;
    this.palette = int(random(3));
    this.drift = int(random(4));
  }
  
  // Draws a word at the current size, color and alpha channel
  void draw() {
    int diff = 5 * ( this.size - FONT_SIZE );
    diff = 0;
    if (diff > 20) {
      //drawBlur();
    }
    
    fill(this.r + diff, this.g + diff, this.b + diff, this.a + diff);
    text(this.w, this.x, this.y);
  }
  
  /** This routine works and produces a nice visual effect, but it is very slow, and will eventually
      run out of memory before the entire corpus has been processed. 
      
  void drawBlur() {
    p = createGraphics(int(textWidth(this.w)) + 40, int(textAscent() + textDescent()) + 40, P3D);
    
    p.beginDraw();  
    p.fill(this.r, this.g, this.b, this.a + 50);
    p.textFont(font);  
    p.textSize(this.size + 2);
    p.text(this.w, 5, 5, int(textWidth(this.w)), int(textAscent() + textDescent()) );
    int diff = this.size - FONT_SIZE;
    if (diff == 0)
      return;
    if (diff > 10)
       diff = 10;  
    p.filter(BLUR, 7);
    p.modified=true;
    p.endDraw();  
    image(p, this.x -5, this.y - textAscent() - 5);
  }
  
  */
  
  /** The normalized form of the word, without common punctuation, and case-insensitive **/
  String normalWord() {
    return this.w.replaceAll(",", "").replaceAll("\\.", "").replaceAll(";", "").toLowerCase();
  }

}

void setup() {
  size(WIDTH, HEIGHT, OPENGL);
  
  font = loadFont("Helvetica-Bold-" + FONT_SIZE + ".vlw"); 
  textFont(font);

  String lines[] = loadStrings("Pride-and-Prejudice_Jane-Austen.txt");
  String sw[] = loadStrings("stopwords.txt");
  for (int i=0;i<sw.length;i++) {
    stopwords.put(sw[i].trim(), ""); 
  }

  for (int i=0; i < lines.length; i++) {
    String l = lines[i];
    String twords[] = l.split(" ");
    for (int j=0;j<twords.length;j++) {
      if (!twords[j].trim().equals(""))
         words.add(twords[j].trim()); 
    }
  }
  println("and " + words.size() + " words ");
  totalWords = words.size();
  frameRate(30);
}

void drawWords() {

  for (Iterator it = displayWords.iterator (); it.hasNext (); ) {
    Word word = (Word)it.next();
  
    int totalFrequency = ((Integer)wordMap.get(word.normalWord())).intValue();
    if ( wordMap.containsKey(word.normalWord()) && ((Integer)wordMap.get(word.normalWord())).intValue() > word.frequency)
    {  

      if (word.palette == RED_PALETTE) {
        word.r = 208; 
        word.g = 168;
        word.b = 37;        
      }
      else if (word.palette == GREEN_PALETTE) {
        word.r = 64;
        word.g = 98;
        word.b = 124;
      }
      else { 
        word.r = 38;
        word.g = 57;
        word.b = 61;
      }

      // Increase alpha channel up to max
      if (word.a < 255) 
        word.a+=10;

      word.size+=2;

      word.frequency++;
    }

    // Use text size to determine the x/y offsetÊ
    int diff = word.size - FONT_SIZE;
    word.x = word.initial_x - diff;

    textSize(word.size);

    if (word.size <= 0) {
      word.a = 0; 
    }

    // If we've left the boundaries, start forcing down the alpha channel
    if  (word.x >= WIDTH || word.y >= HEIGHT)  {
      word.a -= 20; 
    }
    // If we've reached the max size, do the same
    if (word.size >= MAX_SIZE) {
      word.a -= 5; 
    }

    // If we can't see it don't bother drawing it
    if (word.a <= 0) {
      displayMap.remove(word.normalWord());
      it.remove();  
    }
    word.draw();
    textSize(FONT_SIZE);

    if (word.a > 0) {
      word.a-=3;
      
    }
    else {
      word.a = 0; 
    }

  }

}


void draw() {
  background(0);

  s = (String) words.get(index);
  Word word = new Word(s, x, y, r, g, b);
  String normalWord = word.normalWord();
  
    
  if (stopwords.containsKey(normalWord)) {
    // Draw this but don't otherwise add it to any list
    wordMap.put(normalWord, new Integer(1)); 

  }
  else { 
    if (wordMap.containsKey(normalWord)) {
      Integer v = (Integer)wordMap.get(normalWord);
      wordMap.put(normalWord, new Integer(v.intValue() + 1));
      if (!displayMap.containsKey(normalWord)) {
        displayMap.put(normalWord, new Integer(1));
      }
    }
    else {
      wordMap.put(normalWord, new Integer(1)); 
      displayMap.put(normalWord, new Integer(1));
      
    }
    word.frequency =+ 1;
  }
  

  displayWords.add(word);
        
  drawWords();

  int nextWord = int(textWidth((String)words.get(index + 1) + " "));
  int thisWord = int(textWidth(s + " "));

  // Move the x pointer to the next word position
  x+= thisWord;

  // If our new position + the next word's length is greater than our width,
  // move to a new line  
  if ( (x + nextWord) >= WIDTH) {
    // Wrap to next line, if there's room
    y = y + int(textAscent() + textDescent());
    x = MARGIN;    
    
    // We've gotten to the bottom of the page, so start from the top
    if (y + (textAscent() + textDescent())  >= HEIGHT) {
      y = Y_START;
    }
  }
  index++;
  delay(25); 
}
