int HEIGHT = 800;
int WIDTH = 600;
int MARGIN = 5;
int FONT_SIZE = 48;

// Palettes control which color scheme is modified when the
// word "ages"
int RED_PALETTE = 0;
int GREEN_PALETTE = 1;
int BLUE_PALETTE = 2;

int index = 0;
PFont font;
ArrayList words = new ArrayList();
ArrayList displayWords = new ArrayList();
HashMap wordMap = new HashMap();

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

  public Word(String w, int x, int y, int r, int g, int b) {
    this.w = w;
    this.x = x;
    this.y = y;
    this.r = r;
    this.g = g;
    this.b = b;
    this.a = 255;
    this.palette = int(random(3));
    this.drift = int(random(4));

  }
  void draw() {
    fill(this.r, this.g, this.b, this.a);
    text(this.w, this.x, this.y);
  }
  String normalWord() {
    return this.w.replaceAll(",", "").replaceAll("\\.", "").replaceAll(";", "").toLowerCase();
  }

  boolean atMaxColor() {
    return (this.r >= 255);
  }

}

void setup() {
  size(WIDTH, HEIGHT);

  font = loadFont("Helvetica-Bold-" + FONT_SIZE + ".vlw"); 
  textFont(font);
  //textMode(SCREEN);

  String lines[] = loadStrings("ss.txt");

  println("there are " + lines.length + " lines");

  for (int i=0; i < lines.length; i++) {
    String l = lines[i];
    String twords[] = l.split(" ");
    for (int j=0;j<twords.length;j++) {
      words.add(twords[j]); 
    }
  }
  println("and " + words.size() + " words ");
}

void drawWords() {

  for (Iterator it = displayWords.iterator (); it.hasNext (); ) {
    Word word = (Word)it.next();

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
      /*
       switch(word.drift) {
       case 0: 
       if (word.x >= WIDTH) word.x-=2; else word.x+=2;
       case 1: 
       if (word.y >= HEIGHT) word.y-=2; else word.y+=2;
       
       case 2: 
       if (word.x <= 0) word.x+=2; else word.x--;
       case 3: 
       if (word.y <= 0) word.y+=2; else word.y--;
       }
       */
      switch(word.drift) {
      case 0: 
        word.x+=2;
      case 1: 
        word.y+=2;

      case 2: 
        word.x--;
      case 3: 
        word.y--;
      }

      textSize(word.size);
      //word.frequency++;
      //println(word.frequency);

    }
    if (word.a < 0) {
      println("removing " + word.w + " (" + displayWords.size() + ")");
      it.remove();
    }
    // If we've left the boundaries, start forcing down the alpha channel
    if  (word.x >= WIDTH || word.y >= HEIGHT)  {
      word.a -= 20; 
    }
    word.draw();

    textSize(FONT_SIZE);

    if (word.a > 0) {
      //println("Shrinking " + word.w);
      word.size--;
      word.a-=10;

    }
    else {
      word.a = 0; 
    }
  }

}


void draw() {
  background(0);

  drawWords();

  s = (String) words.get(index);
  Word word = new Word(s, x, y, r, g, b);
  String normalWord = word.normalWord();

  if (wordMap.containsKey(normalWord)) {
    Integer v = (Integer)wordMap.get(normalWord);
    wordMap.put(normalWord, new Integer(v.intValue() + 1));
  }
  else {
    wordMap.put(normalWord, new Integer(1)); 
    displayWords.add(word);
    word.draw();

  }
  word.frequency =+ 1;

  /*
  if (index == 2000) {
   exit(); 
   }
   */
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
    if (y + (textAscent() + textDescent())  >= HEIGHT) {
      y = Y_START;
    }
  }
  index++;
  //delay(1); 
}
