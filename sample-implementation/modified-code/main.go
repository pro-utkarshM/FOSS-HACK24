package main

import (
	"encoding/base64"
	"fmt"
	"image"
	"image/png"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"

	"github.com/nfnt/resize"
	"github.com/spf13/cobra"
	"golang.org/x/sys/unix"
)

var rootCmd = &cobra.Command{
	Use:   "icat [directory]",
	Short: "Kitten to display images in a grid layout in Kitty terminal",
	Run:   session,
}

type gridConfig struct {
	xParam int // horizontal parameter
	yParam int // vertical parameter
}

type windowParameters struct {
	Row    uint16
	Col    uint16
	xPixel uint16
	yPixel uint16
}

type navigationParameters struct {
	imageIndex int // Selected image index
	x          int // Horizontal Grid Coordinate
	y          int // Vertical Grid Coordinate
}

var (
	recursive               bool
	maxImages               int
	globalWindowParameters  windowParameters // Contains Global Level Window Parameters
	globalGridConfig        gridConfig
)

func init() {
	rootCmd.Flags().BoolVarP(&recursive, "recursive", "r", false, "Scan directory recursively")
	rootCmd.Flags().IntVarP(&maxImages, "max-images", "n", 100, "Maximum number of images to display")
}

func getWindowSize(window windowParameters) error {
	var err error
	var f *os.File

	if f, err = os.OpenFile("/dev/tty", unix.O_NOCTTY|unix.O_CLOEXEC|unix.O_NDELAY|unix.O_RDWR, 0666); err == nil {
		var sz *unix.Winsize
		if sz, err = unix.IoctlGetWinsize(int(f.Fd()), unix.TIOCGWINSZ); err == nil {
			globalWindowParameters = windowParameters{sz.Row, sz.Col, sz.Xpixel, sz.Ypixel}
			fmt.Printf("rows: %v columns: %v width: %v height %v\n", sz.Row, sz.Col, sz.Xpixel, sz.Ypixel)
			return nil
		}
	}

	fmt.Fprintln(os.Stderr, err)
	return err
}

func handleWindowSizeChange() {
	err := getWindowSize(globalWindowParameters)
	if err != nil {
		fmt.Println("Error handling window size change:", err)
	}
}

func discoverImages(dir string) ([]string, error) {
	var images []string
	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && strings.HasSuffix(strings.ToLower(info.Name()), ".png") {
			images = append(images, path)
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	return images, nil
}

func resizeImage(img image.Image, width, height uint) image.Image {
	return resize.Resize(width, height, img, resize.Lanczos3)
}

func imageToBase64(img image.Image) (string, error) {
	var buf strings.Builder
	err := png.Encode(&buf, img)
	if err != nil {
		return "", err
	}
	return base64.StdEncoding.EncodeToString([]byte(buf.String())), nil
}

func loadImage(filePath string) (image.Image, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	img, _, err := image.Decode(file)
	if err != nil {
		return nil, err
	}
	return img, nil
}

func printImageToKitty(encoded string, width, height int) {
	fmt.Printf("\x1b_Gf=1,t=d,w=%d,h=%d;x=%s\x1b\\", width, height, encoded)
}

func renderImageGrid(images []string, config gridConfig) error {
	if config.xParam == 0 {
		config.xParam = 4 // Default to 4 columns if not provided
	}
	if config.yParam == 0 {
		config.yParam = 4 // Default to 4 rows if not provided
	}

	cols := config.xParam
	rows := config.yParam
	imgWidth := int(globalWindowParameters.xPixel) / cols
	imgHeight := int(globalWindowParameters.yPixel) / rows

	for i, path := range images {
		img, err := loadImage(path)
		if err != nil {
			return fmt.Errorf("error loading image: %v", err)
		}

		resizedImg := resizeImage(img, uint(imgWidth), uint(imgHeight))
		imgBase64, err := imageToBase64(resizedImg)
		if err != nil {
			return fmt.Errorf("error encoding image to base64: %v", err)
		}

		printImageToKitty(imgBase64, imgWidth, imgHeight)

		if (i+1)%cols == 0 {
			fmt.Println() // New line after each row of images
		}
	}
	return nil
}

func handleNavigation(images []string, config gridConfig) error {
	// Implement the navigation logic here
	return nil
}

func session(cmd *cobra.Command, args []string) {
	if len(args) == 0 {
		fmt.Println("Please specify a directory")
		os.Exit(1)
	}

	dir := args[0]
	images, err := discoverImages(dir)
	if err != nil {
		fmt.Printf("Error discovering images: %v\n", err)
		os.Exit(1)
	}

	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGWINCH)

	handleWindowSizeChange()

	go func() {
		for {
			sig := <-sigs
			if sig == syscall.SIGWINCH {
				handleWindowSizeChange()
			}
		}
	}()

	err = renderImageGrid(images, globalGridConfig)
	if err != nil {
		fmt.Printf("Error rendering image grid: %v\n", err)
		os.Exit(1)
	}

	err = handleNavigation(images, globalGridConfig)
	if err != nil {
		fmt.Printf("Error during navigation: %v\n", err)
		os.Exit(1)
	}
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
